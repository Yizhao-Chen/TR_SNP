from rpy2.robjects import FloatVector
from improved_allodb import batch_estimate_biomass, estimate_biomass_using_get_biomass_cached
from bark_dict_species import bark_dict_species
from allometric_dict import *
import rpy2
import tzlocal
import random
from rpy2.robjects import r
from rpy2.robjects.packages import importr
from rpy2.robjects.vectors import StrVector

from rpy2.robjects.packages import importr, data
from rpy2.robjects.vectors import DataFrame, StrVector
from rpy2.robjects.conversion import localconverter
from rpy2.robjects import r, pandas2ri, numpy2ri
import numpy as np
import pandas as pd
from pandas import *
from io import StringIO
import logging
import os
import csv
import time
import tkinter as tk
from tkinter import messagebox

# plot
from matplotlib import pyplot

# import R package
dplR = importr('dplR')
r_base = importr('base')
pandas2ri.activate()
numpy2ri.activate()

# import function to get the site allometric relationships


# Add memoization decorator for expensive functions
def memoize(func):
    cache = {}
    def wrapper(*args):
        key = str(args)
        if key not in cache:
            cache[key] = func(*args)
        return cache[key]
    return wrapper

# Apply memoization to expensive functions
bark_dict_species_original = bark_dict_species
bark_dict_species = memoize(bark_dict_species_original)

# Add biomass calculation caching
biomass_cache = {}
def cached_calculate_biomass_batch(diameter_values, species_code, lat, lon, logger=None):
    # Create a cache key from the parameters
    cache_key = f"{species_code}_{lat}_{lon}"
    
    # Convert diameter_values to tuple for hashability if it's a list
    if isinstance(diameter_values, list):
        diameters_tuple = tuple(diameter_values)
    elif isinstance(diameter_values, np.ndarray):
        diameters_tuple = tuple(diameter_values.tolist())
    else:
        diameters_tuple = (diameter_values,)
    
    # If we have cached values for this species/location
    if cache_key in biomass_cache:
        cached_results = biomass_cache[cache_key]
        # Check if we already calculated this exact diameter
        if diameters_tuple in cached_results:
            return cached_results[diameters_tuple]
    else:
        biomass_cache[cache_key] = {}
    
    # Calculate the biomass
    result = calculate_biomass_batch(diameter_values, species_code, lat, lon, logger)
    
    # Cache the result
    biomass_cache[cache_key][diameters_tuple] = result
    
    return result
# Import bark thickness calculation function

# 导入改进的批处理函数


# 全局缓存，用于存储元数据以避免重复IO操作
SPECIES_CACHE = {}


def process_tree_data(r_result, orig_dataframe=None, years=None, var_type='dia'):
    """处理树木数据并计算均值

    参数:
    r_result: R对象或pandas DataFrame
    orig_dataframe: 原始数据框(用于fallback)
    years: 年份列表(用于fallback)
    var_type: 变量类型，例如'dia'或'dia_0.123'，用于正确命名结果列
    """
    try:
        # 首先检查是否是R对象
        if hasattr(r_result, 'rx2'):
            # 是R对象，直接提取数据
            with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
                year = np.array(r_result.rx2('year'))
                mean_val = np.array(r_result.rx2('std'))
                samp_depth_val = np.array(r_result.rx2('samp.depth'))

                # 创建一致的列名格式 (mean_dia or mean_dia_0.123)
                mean_col_name = f"mean_{var_type}"
                # 创建对应的样本深度列名 (samp.depth_dia or samp.depth_dia_0.123)
                # Let's simplify to just samp.depth_<rand_val> or samp.depth
                if '_' in var_type: # Check if it contains random value suffix
                    rand_val_suffix = var_type.split('_')[-1]
                    samp_depth_col_name = f"samp.depth_{rand_val_suffix}"
                else:
                    samp_depth_col_name = "samp.depth" # Standard name for single simulation
                
                # 这里是关键修复 - 确保使用正确的年份索引
                # 创建一个映射，将R返回的年份索引映射到原始年份
                if orig_dataframe is not None and years is not None:
                    # 确保year和years的长度匹配，可能需要截断或者填充
                    if len(year) <= len(years):
                        # 如果R处理后的数据少于等于原始数据，使用年份前缀对齐
                        result_df = pd.DataFrame({
                            'Year': years[:len(year)],
                            mean_col_name: mean_val,
                            samp_depth_col_name: samp_depth_val
                        })
                    else:
                        # 如果R处理后的数据比原始数据多，需要截断
                        result_df = pd.DataFrame({
                            'Year': years,
                            mean_col_name: mean_val[:len(years)],
                            samp_depth_col_name: samp_depth_val[:len(years)]
                        })
                else:
                    # 如果没有原始数据框和年份，使用R返回的year
                    result_df = pd.DataFrame({
                        'Year': year,
                        mean_col_name: mean_val,
                        samp_depth_col_name: samp_depth_val
                    })

                return result_df
        else:
            # 已经是pandas DataFrame，直接返回
            # 假设r_result已经包含正确的列名 (This part might need review if fallback needs specific samp.depth naming)
            return r_result

    except Exception as e:
        print(f"Error in R-Python conversion: {str(e)}")
        # 确保回退方案有必要的参数
        if orig_dataframe is not None and years is not None:
            # 回退到简单的pandas计算
            mean_col_name = f"mean_{var_type}"
            # Determine fallback samp.depth column name
            if '_' in var_type: 
                rand_val_suffix = var_type.split('_')[-1]
                samp_depth_col_name = f"samp.depth_{rand_val_suffix}"
            else:
                samp_depth_col_name = "samp.depth"
                
            return pd.DataFrame({
                'Year': years,
                mean_col_name: orig_dataframe.mean(axis=1),
                samp_depth_col_name: orig_dataframe.count(axis=1)
            })
        else:
            # 没有足够的信息来创建回退数据框
            print("Warning: Not enough information for fallback calculation")
            return pd.DataFrame()  # 返回空DataFrame

# 优化的生物量计算函数，使用批处理和矢量化操作


def calculate_biomass_batch(
        diameter_values,
        species_code,
        lat,
        lon,
        logger=None):
    """
    批量计算生物量，使用批处理API减少R调用次数

    参数:
    diameter_values: 直径值列表
    species_code: 树种代码
    lat, lon: 坐标
    logger: 日志记录器

    返回:
    生物量值列表
    """
    # 使用批处理API
    try:
        # 检查输入参数
        if not isinstance(diameter_values, (list, np.ndarray)):
            if logger:
                logger.warning(
                    f"diameter_values不是列表或数组类型: {type(diameter_values)}")
            diameter_values = [diameter_values]

        # 确保无NaN/None值
        if isinstance(diameter_values, np.ndarray):
            has_invalid = np.isnan(diameter_values).any()
            if has_invalid:
                if logger:
                    logger.warning(f"diameter_values包含NaN值，将被替换为0.01")
                diameter_values = np.nan_to_num(diameter_values, nan=0.01)
        else:
            valid_values = []
            for v in diameter_values:
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    valid_values.append(0.01)
                else:
                    valid_values.append(v)
            diameter_values = valid_values

        # 确保坐标有效
        if lat is not None and lon is not None:
            coords = (lon, lat)
        else:
            coords = (-76.8, 39.2)  # 默认北美坐标
            if logger:
                logger.info(f"使用默认坐标: {coords}")

        # 获取拉丁名
        latin_name = SPECIES_CODE_MAP.get(species_code, species_code)
        if species_code != latin_name:
            if logger:
                logger.info(f"已将物种代码 {species_code} 映射为拉丁名 {latin_name}")
        else:
            if logger:
                logger.info(f"未找到物种代码 {species_code} 的映射，直接使用该代码")

        # 批量计算
        if logger:
            logger.debug(f"开始批量计算 {len(diameter_values)} 个直径值")

        results = batch_estimate_biomass(
            [diameter_values], latin_name, coords=coords)

        if not results:
            if logger:
                logger.error("批量计算返回空结果")
            raise ValueError("批量计算返回空结果")

        if not results[0].empty:
            if logger:
                logger.debug(f"批量计算成功，返回 {len(results[0]['agb'])} 个结果")

            # 确保结果长度与输入长度相同
            if len(results[0]['agb']) != len(diameter_values):
                if logger:
                    logger.warning(
                        f"结果长度 ({len(results[0]['agb'])}) 与输入长度 ({len(diameter_values)}) 不匹配")

                # 填充结果到正确长度
                output_values = np.full(len(diameter_values), np.nan)
                min_len = min(len(results[0]['agb']), len(diameter_values))
                output_values[:min_len] = results[0]['agb'].values[:min_len]
                return output_values

            return results[0]['agb'].values
        else:
            if logger:
                logger.warning("批量计算结果为空，回退到逐一计算")

        # 如果批处理失败，退回到逐一计算
        biomass_values = []
        for dbh in diameter_values:
            biomass = allometric_dict(dbh, species_code, lat, lon, logger)
            biomass_values.append(biomass)

        if logger:
            logger.debug(f"逐一计算完成，返回 {len(biomass_values)} 个结果")

        return np.array(biomass_values)

    except Exception as e:
        error_msg = f"批量计算生物量出错: {e}"
        print(error_msg)
        if logger:
            logger.error(error_msg, exc_info=True)

        # 退回到逐一计算，包含异常处理
        biomass_values = []
        for dbh in diameter_values:
            try:
                biomass = allometric_dict(dbh, species_code, lat, lon, logger)
                biomass_values.append(biomass)
            except Exception as e2:
                if logger:
                    logger.error(f"计算单个生物量时出错: dbh={dbh}, error={e2}")
                biomass_values.append(np.nan)

        return np.array(biomass_values)


def plot_allometry_species(
        fk,
        min_value,
        max_value,
        times,
        file_Column_Randoms,
        dbh_method,
        bark_method,
        output_path,
        site_ids,
        regionls,
        speciesls,
        latls,
        lonls,
        geometric_correction_rates=None,
        bark_correction_rates=None,
        default_geometric_rate=1.0,
        default_bark_rate=0.05):
    """
    处理树木生物量计算和绘图 - 优化版本 (适用于自定义物种)

    参数说明:
    - site_ids: 站点ID列表，用于匹配文件与站点信息
    - bark_method: 树皮处理方法
        - -1: 自定义处理 (Custom)
        - 0: 不处理树皮 (No)
        - 1: 基于生物计量学处理 (Allometry)

    - geometric_correction_rates: 每个文件的每个样本的几何校正率字典列表
    - bark_correction_rates: 每个文件的每个样本的树皮校正率字典列表
    - default_geometric_rate: 默认几何校正率
    - default_bark_rate: 默认树皮校正率

    注意: 当bark_method=1时，使用bark_dict_species函数计算树皮厚度。
    """
    start_time = time.time()
    print(f"Correction Value:", min_value, max_value, times)
    print(f"dbh_method: {dbh_method}")
    print(f"bark_method: {bark_method}")
    print(f"output_path: {output_path}")
    
    # Log site IDs and their corresponding parameters
    for i, site_id in enumerate(site_ids):
        print(f"Site ID: {site_id}, Region: {regionls[i]}, Species: {speciesls[i]}, Lat: {latls[i]}, Lon: {lonls[i]}")

    # Debug print the geometric_correction_rates
    print("\n=== DEBUG: GEOMETRIC CORRECTION RATES ===")
    if geometric_correction_rates:
        for idx, rates in enumerate(geometric_correction_rates):
            if rates:
                print(f"File #{idx}: {type(rates)}, {len(rates)} rate entries")
                if isinstance(rates, dict) and len(rates) > 0:
                    # Print first 5 items or fewer if less available
                    sample_items = list(rates.items())[:min(5, len(rates))]
                    print(f"Sample entries: {sample_items}")
            else:
                print(f"File #{idx}: No rates defined")
    else:
        print("No geometric correction rates defined")
    print("=======================================\n")
    
    # Initialize correction rates if not provided
    if geometric_correction_rates is None:
        geometric_correction_rates = [{} for _ in fk]
    if bark_correction_rates is None:
        bark_correction_rates = [{} for _ in fk]

    # 初始化日志记录器
    logger = logging.getLogger('biomass_estimation')
    logger.setLevel(logging.INFO)

    # 创建日志文件处理器
    log_file = os.path.join(output_path, 'biomass_processing.log')
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)

    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)

    # 如果logger没有处理器,添加处理器
    if not logger.handlers:
        logger.addHandler(fh)

    logger.info(f"开始处理生物量计算 - 参数配置:")
    logger.info(f"Correction Value: {min_value}, {max_value}, {times}")
    logger.info(f"DBH method: {dbh_method}")
    logger.info(f"Bark method: {bark_method}")
    logger.info(f"Output path: {output_path}")
    
    # Log the geometric correction rates
    logger.info("=== GEOMETRIC CORRECTION RATES ===")
    if geometric_correction_rates:
        for idx, rates in enumerate(geometric_correction_rates):
            if rates:
                logger.info(f"File #{idx}: {type(rates)}, {len(rates)} rate entries")
                if isinstance(rates, dict) and len(rates) > 0:
                    # Log first 5 items or fewer if less available
                    sample_items = list(rates.items())[:min(5, len(rates))]
                    logger.info(f"Sample entries: {sample_items}")
            else:
                logger.info(f"File #{idx}: No rates defined")
    else:
        logger.info("No geometric correction rates defined")
    logger.info("=======================================")

    pyplot.rcParams['savefig.dpi'] = 300
    pyplot.rcParams['figure.dpi'] = 300
    # Remove global figure initialization - we'll create per-site figures
    # pyplot.figure()

    # 记录处理时间和总文件数，用于估算剩余时间
    total_files = len(fk)
    processed_files = 0

    for indexF in range(len(fk)):
        # Create a new figure for each site
        pyplot.figure()
        
        file_start_time = time.time()
        TR_input_dir = fk[indexF]
        # get the file name without direction and extension
        mm = os.path.splitext(os.path.basename(fk[indexF]))[0]

        # Get site-specific information using index
        site_id = site_ids[indexF]
        region = regionls[indexF]
        species = speciesls[indexF]
        lat = latls[indexF]
        lon = lonls[indexF]

        logger.info(f"开始处理文件: {mm} (Site ID: {site_id})")
        print(f"Processing {mm} (Site ID: {site_id})")
        logger.info(f"站点信息: Region={region}, Species={species}, Lat={lat}, Lon={lon}")

        # 使用传入的物种代码和坐标，而不是从元数据中查找
        species_code = species

        TR_input = r['read.tucson'](TR_input_dir)
        start = r['min'](r['as.numeric'](r['rownames'](TR_input)))
        end = r['max'](r['as.numeric'](r['rownames'](TR_input)))

        # 优化: 一次性获取年份范围
        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
            t_start = float(start[0])
            t_end = float(end[0])
            years = range(int(t_start), int(t_end) + 1)

            # 一次性转换 R 数据框为 pandas
            pdf_input = pandas2ri.rpy2py(TR_input)
            pdf_input.index = years
            pdf_input.insert(0, "Year", years)
            pdf_input = pdf_input.drop(pdf_input.columns[0], axis=1)

        # 初始化收集数据的字典，用于减少DataFrame碎片化
        data_columns = {
            'dia': {'Year': years},
            'bio': {'Year': years},
            'delta_dia': {'Year': years},
            'delta_bio': {'Year': years},
            'diaa': {'Year': years},
            'bioo': {'Year': years},
            'delta_diaa': {'Year': years},
            'delta_bioo': {'Year': years},
            'age': {'Year': years}
        }
        
        # Initialize dataframes dictionary to store all DataFrames
        dataframes = {}

        # 记录每列的第一个非空值索引，优化后续计算
        first_valid_indices = {}
        for i, col in enumerate(pdf_input.columns):
            first_valid_indices[i] = pdf_input.iloc[:, i].first_valid_index()

        # 生成随机值列表 - 使用集合保证唯一性
        random_values = []
        if times > 0:
            # 使用集合保证唯一性
            random_value_set = set()
            while len(random_value_set) < times:
                random_value = round(random.uniform(min_value, max_value), 3)
                random_value_set.add(random_value)
            random_values = list(random_value_set)
        else:
            # times = 0 或 times < 0 时，只使用一个固定的随机值
            random_values = [0]

        print("random_values = ", random_values)
        logger.info(f"Using random values: {random_values}")

        for rand_val in random_values:
            print("rand_val = ", rand_val)
            logger.info(f"Processing random value: {rand_val}")

            # Process each random value and store results in temporary
            # dataframes
            for i in range(len(pdf_input.columns)):
                col_start_time = time.time()
                # 提取一列数据并创建副本
                pdf_sub = pdf_input.iloc[:, i].copy()
                column_name = pdf_input.columns[i]

                # 获取该列的第一个和最后一个非NaN值的索引
                y_start = first_valid_indices[i]
                y_end = pdf_sub.last_valid_index()

                if y_start is None or y_end is None:
                    continue  # 跳过全是NaN的列

                # 为当前样本获取自定义校正率
                user_geometric_rate = default_geometric_rate
                user_bark_rate = default_bark_rate

                # Get sample name (column name in the dataframe)
                column_name = pdf_input.columns[i]
                
                # EXTENSIVE DEBUGGING FOR GEOMETRIC RATES
                logger.info(f"======= DEBUGGING GEOMETRIC RATES FOR SAMPLE {column_name} =======")
                if geometric_correction_rates and len(geometric_correction_rates) > indexF:
                    logger.info(f"Geometric correction rates available for file #{indexF}")
                    if isinstance(geometric_correction_rates[indexF], dict):
                        logger.info(f"Correction rates stored as dictionary with {len(geometric_correction_rates[indexF])} entries")
                        logger.info(f"Available keys: {list(geometric_correction_rates[indexF].keys())}")
                        if column_name in geometric_correction_rates[indexF]:
                            logger.info(f"MATCH FOUND! Sample name '{column_name}' exists in correction rates")
                        else:
                            logger.info(f"No match for sample '{column_name}' in correction rates dictionary")
                    else:
                        logger.info(f"Correction rates not stored as dictionary but as: {type(geometric_correction_rates[indexF])}")
                else:
                    logger.info(f"No geometric correction rates defined for file #{indexF}")
                
                # Look up geometric correction rate by sample name if available
                if geometric_correction_rates and len(geometric_correction_rates) > indexF and isinstance(geometric_correction_rates[indexF], dict):
                    # First try to find by sample name (column_name)
                    if column_name in geometric_correction_rates[indexF]:
                        prev_rate = user_geometric_rate
                        user_geometric_rate = geometric_correction_rates[indexF][column_name]
                        logger.info(f"Applied custom geometric rate for sample {column_name}: changed from {prev_rate} to {user_geometric_rate}")
                    # Fall back to index-based lookup for backward compatibility
                    elif i in geometric_correction_rates[indexF]:
                        prev_rate = user_geometric_rate
                        user_geometric_rate = geometric_correction_rates[indexF][i]
                        logger.info(f"Applied index-based geometric rate for sample {column_name}: changed from {prev_rate} to {user_geometric_rate}")
                else:
                    logger.info(f"Using default geometric rate for sample {column_name}: {user_geometric_rate}")

                # 检查是否有为该样本设置的自定义树皮校正率
                if bark_correction_rates and len(bark_correction_rates) > indexF and isinstance(bark_correction_rates[indexF], dict):
                    # First try to find by sample name
                    if column_name in bark_correction_rates[indexF]:
                        user_bark_rate = bark_correction_rates[indexF][column_name]
                        logger.info(f"Using custom bark rate for sample {column_name}: {user_bark_rate}")
                    # Fall back to index-based lookup for backward compatibility
                    elif i in bark_correction_rates[indexF]:
                        user_bark_rate = bark_correction_rates[indexF][i]
                        logger.info(f"Using index-based bark rate for sample {column_name}: {user_bark_rate}")
                else:
                    logger.info(f"Using default bark rate for sample {column_name}: {user_bark_rate}")
                    
                # 初始化向量
                diameter = pd.Series(np.nan, index=pdf_sub.index)
                diameterr = pd.Series(np.nan, index=pdf_sub.index)
                diameterr_geo = pd.Series(np.nan, index=pdf_sub.index)  # Initialize diameterr_geo
                diameterr_geo_bark = pd.Series(np.nan, index=pdf_sub.index)  # Initialize diameterr_geo_bark
                biomass = pd.Series(np.nan, index=pdf_sub.index)
                biomasss = pd.Series(np.nan, index=pdf_sub.index)
                delta_dia = pd.Series(np.nan, index=pdf_sub.index)
                delta_diaa = pd.Series(np.nan, index=pdf_sub.index)
                delta_bio = pd.Series(np.nan, index=pdf_sub.index)
                delta_bioo = pd.Series(np.nan, index=pdf_sub.index)
                age = pd.Series(np.nan, index=pdf_sub.index)

                # 分别处理第一年和后续年份
                # 第一年
                if pdf_sub[y_start] == 0:
                    pdf_sub[y_start] = 1e-8

                # 添加随机宽度
                # 为保留原始数据，创建一个带有初始宽度修正的副本用于计算diaa相关指标
                pdf_sub_corrected = pdf_sub.copy()

                # 只有在有效的条件下才应用初始宽度校正
                if times < 0 and file_Column_Randoms is not None and indexF < len(
                        file_Column_Randoms) and file_Column_Randoms[indexF] is not None and i < len(file_Column_Randoms[indexF]):
                    # 只对校正后的数据应用初始宽度偏差
                    pdf_sub_corrected[y_start] = pdf_sub_corrected[y_start] + \
                        file_Column_Randoms[indexF][i]
                elif times > 0:
                    # 随机校正
                    pdf_sub_corrected[y_start] = pdf_sub_corrected[y_start] + rand_val

                # 初始年龄和直径
                age[y_start] = 1

                # 计算原始直径 (无校正)
                diameter[y_start] = (2 * pdf_sub[y_start]) / 10  # cm

                # 计算校正后的直径 (应用了初始宽度校正)
                diameterr[y_start] = (2 * pdf_sub_corrected[y_start]) / 10  # cm

                # geometric correction
                if dbh_method == -1:
                    # No correction for both
                    diameterr_geo[y_start] = diameterr[y_start]
                    logger.info(f"No geometric correction applied - Sample: {column_name}, Diameter: {diameterr[y_start]:.4f} cm")
                elif dbh_method == 0:
                    # Lockwood et al.,2021方程
                    orig_value = diameterr[y_start]
                    diameterr_geo[y_start] = diameterr[y_start] * 0.998 + 22.3
                    logger.info(f"Lockwood geometric correction - Sample: {column_name}, Original: {orig_value:.4f} cm, Corrected: {diameterr_geo[y_start]:.4f} cm")
                elif dbh_method == 1:
                    # user defined correction rate
                    orig_value = diameterr[y_start]
                    diameterr_geo[y_start] = diameterr[y_start] * user_geometric_rate
                    logger.info(
                        f"Custom geometric correction - Sample: {column_name}, Original: {orig_value:.4f} cm, Rate: {user_geometric_rate}, Corrected: {diameterr_geo[y_start]:.4f} cm")

                # bark correction
                if bark_method == -1:
                    # Custom bark thickness based on user-defined rate
                    #original_diameter = diameterr[y_start]
                    bark_thickness = diameterr_geo[y_start] * user_bark_rate
                    diameterr_geo_bark[y_start] = diameterr_geo[y_start] + bark_thickness
                    logger.info(
                        f"Custom bark correction - Sample: {column_name}, Original diameter: {diameterr_geo[y_start]:.4f} cm, Rate: {user_bark_rate}, Bark thickness: {bark_thickness:.4f} cm, Corrected: {diameterr_geo[y_start]:.4f} cm")
                elif bark_method == 0:
                    # No bark correction
                    diameterr_geo_bark[y_start] = diameterr_geo[y_start]
                elif bark_method == 1:
                    # Allometry-based bark correction using bark_dict_species
                    # function
                    bark_thickness = bark_dict_species(
                        region, species_code, diameterr[y_start])
                    logger.info(
                        f"Initial bark correction - Species: {species_code}, Sample: {column_name}, Original diameter: {diameterr[y_start]:.4f} cm, Bark thickness: {bark_thickness:.4f} cm, Corrected: {diameterr[y_start] + bark_thickness:.4f} cm")
                    diameterr_geo_bark[y_start] = diameterr_geo[y_start] + bark_thickness

                # 批量计算后续年份的直径
                for k in range(y_start + 1, y_end + 1):
                    if pd.isna(pdf_sub[k]):
                        continue

                    # 替换零值
                    if pdf_sub[k] == 0:
                        pdf_sub[k] = 1e-8

                    # 同样替换校正数据中的零值
                    if pdf_sub_corrected[k] == 0:
                        pdf_sub_corrected[k] = 1e-8

                    # 计算年龄和累积直径
                    if not pd.isna(age[k - 1]):
                        age[k] = age[k - 1] + 1

                    # 计算原始直径 (无校正)
                    diameter[k] = diameter[k - 1] + (2 * pdf_sub[k]) / 10

                    # 计算校正后的直径 (应用了初始宽度校正)
                    diameterr[k] = diameterr[k - 1] + \
                        (2 * pdf_sub_corrected[k]) / 10
                    

                    # geometric correction
                    if dbh_method == -1:
                        diameterr_geo[k] = diameterr[k]
                    elif dbh_method == 0:
                        # Lockwood et al.,2021方程
                        diameterr_geo[k] = diameterr[k] * 0.998 + 22.3
                        if k % 20 == 0: # Log only every 20th entry to avoid excessive logging
                            logger.info(f"Year {k} Lockwood correction - Sample: {column_name}, Original: {diameterr[k]:.4f} cm, Corrected: {diameterr_geo[k]:.4f} cm")
                    elif dbh_method == 1:
                        # user defined correction rate
                        orig_value = diameterr[k]
                        diameterr_geo[k] = diameterr[k] * user_geometric_rate
                        if k % 20 == 0: # Log only every 20th entry to avoid excessive logging
                            logger.info(f"Year {k} custom geometric correction - Sample: {column_name}, Original: {orig_value:.4f} cm, Rate: {user_geometric_rate}, Corrected: {diameterr_geo[k]:.4f} cm")

                    # bark correction
                    if bark_method == -1:
                        # Custom bark thickness based on user-defined rate
                        #original_diameter = diameterr[k]
                        bark_thickness = diameterr_geo[k] * user_bark_rate
                        diameterr_geo_bark[k] = diameterr_geo[k] + bark_thickness
                        if k % 20 == 0:  # Log less frequently to avoid excessive logging
                            logger.info(
                                f"Year {k} custom bark correction - Sample: {column_name}, Original diameter: {diameterr_geo[k]:.4f} cm, Rate: {user_bark_rate}, Bark thickness: {bark_thickness:.4f} cm, Corrected: {diameterr_geo[k]:.4f} cm")
                    elif bark_method == 0:
                        # No bark correction
                        diameterr_geo_bark[k] = diameterr_geo[k]
                    elif bark_method == 1:
                        # Allometry-based bark correction using bark_dict_species
                        # function
                        bark_thickness = bark_dict_species(
                            region, species_code, diameterr[k])
                        if k % 20 == 0:  # Log only every 20th entry to avoid excessive logging
                            logger.info(
                                f"Year {k} bark correction - Species: {species_code}, Sample: {column_name}, Original diameter: {diameterr_geo[k]:.4f} cm, Bark thickness: {bark_thickness:.4f} cm, Corrected: {diameterr_geo[k] + bark_thickness:.4f} cm")
                        diameterr_geo_bark[k] = diameterr_geo[k] + bark_thickness

                # 计算直径增量
                delta_dia[y_start] = diameter[y_start]
                delta_diaa[y_start] = diameterr_geo_bark[y_start]

                # 计算后续年份的直径增量
                for k in range(y_start + 1, y_end + 1):
                    if not pd.isna(diameter[k]) and not pd.isna(diameter[k - 1]):
                        delta_dia[k] = diameter[k] - diameter[k - 1]
                    if not pd.isna(diameterr_geo_bark[k]) and not pd.isna(diameterr_geo_bark[k - 1]):
                        delta_diaa[k] = diameterr_geo_bark[k] - diameterr_geo_bark[k - 1]

                # 批量计算生物量 - 使用批处理函数
                valid_indices = ~diameter.isna()
                valid_diameters = diameter[valid_indices].values

                if len(valid_diameters) > 0:
                    try:
                        biomass_values = cached_calculate_biomass_batch(
                            valid_diameters, species_code, lat, lon, logger)

                        # 检查长度是否匹配
                        if len(biomass_values) == sum(valid_indices):
                            biomass[valid_indices] = biomass_values
                        else:
                            logger.error(
                                f"生物量计算结果长度不匹配: 预期 {sum(valid_indices)}, 实际 {len(biomass_values)}")
                            # 回退到逐个赋值以避免长度不匹配错误
                            valid_idx_positions = np.where(valid_indices)[0]
                            for j, pos in enumerate(valid_idx_positions):
                                if j < len(biomass_values):
                                    biomass.iloc[pos] = biomass_values[j]
                    except Exception as e:
                        logger.error(f"计算生物量时出错: {str(e)}")
                        # 使用默认值或保持NaN

                valid_indices = ~diameterr_geo_bark.isna()  # Changed from diameterr to diameterr_geo_bark
                valid_diameters = diameterr_geo_bark[valid_indices].values  # Changed from diameterr to diameterr_geo_bark

                if len(valid_diameters) > 0:
                    try:
                        biomasss_values = cached_calculate_biomass_batch(
                            valid_diameters, species_code, lat, lon, logger)

                        # 检查长度是否匹配
                        if len(biomasss_values) == sum(valid_indices):
                            biomasss[valid_indices] = biomasss_values
                        else:
                            logger.error(
                                f"校正生物量计算结果长度不匹配: 预期 {sum(valid_indices)}, 实际 {len(biomasss_values)}")
                            # 回退到逐个赋值以避免长度不匹配错误
                            valid_idx_positions = np.where(valid_indices)[0]
                            for j, pos in enumerate(valid_idx_positions):
                                if j < len(biomasss_values):
                                    biomasss.iloc[pos] = biomasss_values[j]
                    except Exception as e:
                        logger.error(f"计算校正生物量时出错: {str(e)}")
                        # 使用默认值或保持NaN

                # 计算生物量增量
                delta_bio[y_start] = biomass[y_start]
                delta_bioo[y_start] = biomasss[y_start]
                
                # 计算后续年份的生物量增量
                for k in range(y_start + 1, y_end + 1):
                    if not pd.isna(biomass[k]) and not pd.isna(biomass[k - 1]):
                        delta_bio[k] = biomass[k] - biomass[k - 1]
                    if not pd.isna(biomasss[k]) and not pd.isna(biomasss[k - 1]):
                        delta_bioo[k] = biomasss[k] - biomasss[k - 1]

                # 将处理结果保存到数据字典中，而不是立即添加到DataFrame中
                # 为列名添加随机值标识
                rand_suffix = f"_{rand_val}" if times > 0 else ""

                # 存入字典而不是立即添加到DataFrame
                col_key = f"dia{rand_suffix}_{column_name}"
                data_columns['dia'][col_key] = diameter

                col_key = f"bio{rand_suffix}_{column_name}"
                data_columns['bio'][col_key] = biomass

                col_key = f"delta_dia{rand_suffix}_{column_name}"
                data_columns['delta_dia'][col_key] = delta_dia

                col_key = f"delta_bio{rand_suffix}_{column_name}"
                data_columns['delta_bio'][col_key] = delta_bio

                col_key = f"diaa{rand_suffix}_{column_name}"
                data_columns['diaa'][col_key] = diameterr

                col_key = f"bioo{rand_suffix}_{column_name}"
                data_columns['bioo'][col_key] = biomasss

                col_key = f"delta_diaa{rand_suffix}_{column_name}"
                data_columns['delta_diaa'][col_key] = delta_diaa

                col_key = f"delta_bioo{rand_suffix}_{column_name}"
                data_columns['delta_bioo'][col_key] = delta_bioo

                col_key = f"age{rand_suffix}_{column_name}"
                data_columns['age'][col_key] = age

        # 完成数据收集后，一次性创建DataFrame，避免频繁插入列导致的碎片化
        for key in ['dia', 'bio', 'delta_dia', 'delta_bio', 'diaa', 'bioo', 'delta_diaa', 'delta_bioo', 'age']:
            dataframes[key] = pd.DataFrame(data_columns[key])
        
        # Process each variable type to calculate means
        for var_type in ['dia', 'bio', 'delta_dia', 'delta_bio', 'diaa', 'bioo', 'delta_diaa', 'delta_bioo', 'age']:
            var_df = dataframes[var_type]
            # Get all sample columns (excluding 'Year') for this variable type
            all_sample_cols = [col for col in var_df.columns if col != 'Year'] 

            if not all_sample_cols:
                logger.warning(f"No sample columns found for {var_type}")
                dataframes[f'{var_type}_mean'] = pd.DataFrame({'Year': years}) # Store empty mean df
                continue

            # Initialize the mean output dataframe for this variable type
            mean_output_df = pd.DataFrame({'Year': years})
            
            # Check if we have multiple simulations (times > 0 and more than one random value)
            if times > 0 and len(random_values) > 1:
                logger.info(f"Calculating {var_type} means and sample depths for {len(random_values)} simulations.")
                
                # --- Multiple Simulations Logic ---
                # mean_output_df starts with just 'Year' column
                for rand_val in random_values:
                    rand_suffix = f"_{rand_val}_"
                    sim_sample_cols = [col for col in all_sample_cols if rand_suffix in col]

                    if not sim_sample_cols:
                        logger.warning(f"No sample columns found for {var_type} simulation {rand_val}")
                        continue
                        
                    logger.debug(f"Processing {var_type} mean & depth for sim {rand_val} using {len(sim_sample_cols)} columns.")
                    
                    # Define expected column names from process_tree_data
                    sim_mean_col_name = f"mean_{var_type}_{rand_val}"
                    sim_samp_depth_col_name = f"samp.depth_{rand_val}"

                    try:
                        # Try R biweight mean for this simulation's samples
                        sample_data = var_df[sim_sample_cols]
                        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
                            r_df = pandas2ri.py2rpy(sample_data)
                            r_result = dplR.chron(r_df) 
                            
                        # Process result using temp var_type to get suffixed columns
                        temp_process_var_type = f"{var_type}_{rand_val}"
                        sim_mean_df_from_r = process_tree_data(r_result, sample_data, years, temp_process_var_type)
                        
                        # Check if BOTH expected columns are returned by process_tree_data
                        if sim_mean_col_name in sim_mean_df_from_r.columns and sim_samp_depth_col_name in sim_mean_df_from_r.columns:
                            mean_values = sim_mean_df_from_r[sim_mean_col_name].values
                            samp_depth_values = sim_mean_df_from_r[sim_samp_depth_col_name].values
                            
                            # Add this simulation's mean column
                            if len(mean_values) >= len(years):
                                mean_output_df[sim_mean_col_name] = mean_values[:len(years)]
                            else: 
                                padded = np.full(len(years), np.nan)
                                padded[:len(mean_values)] = mean_values
                                mean_output_df[sim_mean_col_name] = padded
                                
                            # Add this simulation's sample depth column
                            if len(samp_depth_values) >= len(years):
                                mean_output_df[sim_samp_depth_col_name] = samp_depth_values[:len(years)]
                            else: 
                                padded_sd = np.full(len(years), np.nan)
                                padded_sd[:len(samp_depth_values)] = samp_depth_values
                                mean_output_df[sim_samp_depth_col_name] = padded_sd
                                
                            logger.info(f"Processed {sim_mean_col_name} and {sim_samp_depth_col_name} using R biweight mean.")
                        else:
                             # Error if expected columns aren't returned
                             missing_cols = [c for c in [sim_mean_col_name, sim_samp_depth_col_name] if c not in sim_mean_df_from_r.columns]
                             raise ValueError(f"Columns {missing_cols} not found in R result processing for sim {rand_val}.")

                    except Exception as e:
                        logger.warning(f"R processing failed for sim {rand_val}, falling back to pandas: {e}")
                        # Fallback to pandas mean and count for this simulation
                        mean_values = var_df[sim_sample_cols].mean(axis=1).values
                        samp_depth_values = var_df[sim_sample_cols].count(axis=1).values
                        
                        # Add mean column
                        if len(mean_values) >= len(years):
                            mean_output_df[sim_mean_col_name] = mean_values[:len(years)]
                        else:
                            padded = np.full(len(years), np.nan)
                            padded[:len(mean_values)] = mean_values
                            mean_output_df[sim_mean_col_name] = padded
                            
                        # Add sample depth column
                        if len(samp_depth_values) >= len(years):
                            mean_output_df[sim_samp_depth_col_name] = samp_depth_values[:len(years)]
                        else:
                            padded_sd = np.full(len(years), np.nan)
                            padded_sd[:len(samp_depth_values)] = samp_depth_values
                            mean_output_df[sim_samp_depth_col_name] = padded_sd
                
                # --- End of Multiple Simulations Logic ---
                # No overall samp.depth calculation needed here anymore
                
            else:
                # --- Single Simulation or times <= 0 Logic --- (Remains mostly the same)
                logger.info(f"Calculating overall {var_type} mean and sample depth across {len(all_sample_cols)} samples.")
                mean_col_name = f"mean_{var_type}" 
                samp_depth_col_name = "samp.depth" # Standard name
                
                try:
                    sample_data = var_df[all_sample_cols]
                    with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
                        r_df = pandas2ri.py2rpy(sample_data)
                        r_result = dplR.chron(r_df)
                        
                    # process_tree_data will return mean_col_name and samp_depth_col_name
                    mean_df_from_r = process_tree_data(r_result, sample_data, years, var_type)
                    
                    if mean_col_name in mean_df_from_r.columns and samp_depth_col_name in mean_df_from_r.columns:
                        mean_values = mean_df_from_r[mean_col_name].values
                        samp_depth_values = mean_df_from_r[samp_depth_col_name].values
                        
                        # Add mean column
                        if len(mean_values) >= len(years):
                            mean_output_df[mean_col_name] = mean_values[:len(years)]
                        else: 
                            padded = np.full(len(years), np.nan)
                            padded[:len(mean_values)] = mean_values
                            mean_output_df[mean_col_name] = padded
                        
                        # Add sample depth column (should be last)
                        if len(samp_depth_values) >= len(years):
                             mean_output_df[samp_depth_col_name] = samp_depth_values[:len(years)]
                        else: 
                             padded_sd = np.full(len(years), np.nan)
                             padded_sd[:len(samp_depth_values)] = samp_depth_values
                             mean_output_df[samp_depth_col_name] = padded_sd
                             
                        logger.info(f"Processed {mean_col_name} and {samp_depth_col_name} using R biweight mean")
                    else:
                        missing_cols = [c for c in [mean_col_name, samp_depth_col_name] if c not in mean_df_from_r.columns]
                        logger.warning(f"R result missing {missing_cols}, falling back to pandas mean/count.")
                        # Fallback to pandas mean and count
                        mean_values = sample_data.mean(axis=1).values
                        samp_depth_values = sample_data.count(axis=1).values
                        if len(mean_values) >= len(years):
                             mean_output_df[mean_col_name] = mean_values[:len(years)]
                        else: 
                             padded = np.full(len(years), np.nan)
                             padded[:len(mean_values)] = mean_values
                             mean_output_df[mean_col_name] = padded
                        if len(samp_depth_values) >= len(years):
                             mean_output_df[samp_depth_col_name] = samp_depth_values[:len(years)]
                        else:
                             padded_sd = np.full(len(years), np.nan)
                             padded_sd[:len(samp_depth_values)] = samp_depth_values
                             mean_output_df[samp_depth_col_name] = padded_sd
                        
                except Exception as e:
                    logger.error(f"Error calculating overall {var_type} mean/depth: {str(e)}")
                    # Fallback to pandas mean and count
                    mean_values = var_df[all_sample_cols].mean(axis=1).values
                    samp_depth_values = var_df[all_sample_cols].count(axis=1).values
                    # Add mean column
                    if len(mean_values) >= len(years):
                        mean_output_df[mean_col_name] = mean_values[:len(years)]
                    else: 
                        padded = np.full(len(years), np.nan)
                        padded[:len(mean_values)] = mean_values
                        mean_output_df[mean_col_name] = padded
                    # Add sample depth column
                    if len(samp_depth_values) >= len(years):
                        mean_output_df[samp_depth_col_name] = samp_depth_values[:len(years)]
                    else:
                        padded_sd = np.full(len(years), np.nan)
                        padded_sd[:len(samp_depth_values)] = samp_depth_values
                        mean_output_df[samp_depth_col_name] = padded_sd
                    logger.info(f"Used pandas fallback for overall {var_type} mean/depth due to error.")

            # Store the resulting mean dataframe
            dataframes[f'{var_type}_mean'] = mean_output_df

        # Assign all the final dataframes (including the potentially modified mean ones)
        final_dia = dataframes['dia']
        final_bio = dataframes['bio']
        final_delta_dia = dataframes['delta_dia']
        final_delta_bio = dataframes['delta_bio']
        final_diaa = dataframes['diaa']
        final_bioo = dataframes['bioo']
        final_delta_diaa = dataframes['delta_diaa']
        final_delta_bioo = dataframes['delta_bioo']
        final_age = dataframes['age']
        
        final_dia_mean = dataframes['dia_mean']
        final_bio_mean = dataframes['bio_mean']
        final_delta_dia_mean = dataframes['delta_dia_mean']
        final_delta_bio_mean = dataframes['delta_bio_mean']
        final_diaa_mean = dataframes['diaa_mean']
        final_bioo_mean = dataframes['bioo_mean']
        final_delta_diaa_mean = dataframes['delta_diaa_mean']
        final_delta_bioo_mean = dataframes['delta_bioo_mean']
        final_age_mean = dataframes['age_mean']

        # 保存结果到CSV文件
        region_suffix = region if region != "all" else ""
        species_suffix = species if species != "all" else ""
        file_prefix = f"{mm}_{region_suffix}_{species_suffix}"

        # 设置各种校正选项的编码
        # 2=Random, 1=Customize, 0=No
        initial_width_code = 2 if times > 0 else 1 if times < 0 else 0
        geometric_code = 0 if dbh_method == - \
            1 else 1 if dbh_method == 0 else 2  # 0=No, 1=Lockwood, 2=Customize
        # 0=No, 1=Allometry, 2=Customize
        bark_code = 0 if bark_method == 0 else 1 if bark_method == 1 else 2

        # 保存非校正文件 - 标准格式
        output_file = os.path.join(output_path, f"{file_prefix}_dia.csv")
        final_dia.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(output_path, f"{file_prefix}_bio.csv")
        final_bio.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(output_path, f"{file_prefix}_delta_dia.csv")
        final_delta_dia.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(output_path, f"{file_prefix}_delta_bio.csv")
        final_delta_bio.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(output_path, f"{file_prefix}_age.csv")
        final_age.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        # 保存校正文件 - 包含校正代码
        output_file = os.path.join(
            output_path,
            f"{file_prefix}_diaa_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv")
        final_diaa.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(
            output_path,
            f"{file_prefix}_bioo_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv")
        final_bioo.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(
            output_path,
            f"{file_prefix}_delta_diaa_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv")
        final_delta_diaa.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(
            output_path,
            f"{file_prefix}_delta_bioo_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv")
        final_delta_bioo.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        # 保存均值数据框 - 标准格式
        output_file = os.path.join(output_path, f"{file_prefix}_dia_mean.csv")
        final_dia_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(output_path, f"{file_prefix}_bio_mean.csv")
        final_bio_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(
            output_path,
            f"{file_prefix}_delta_dia_mean.csv")
        final_delta_dia_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(
            output_path,
            f"{file_prefix}_delta_bio_mean.csv")
        final_delta_bio_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(output_path, f"{file_prefix}_age_mean.csv")
        final_age_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        # 保存均值校正数据框 - 包含校正代码
        output_file = os.path.join(
            output_path,
            f"{file_prefix}_diaa_mean_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv")
        final_diaa_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(
            output_path,
            f"{file_prefix}_bioo_mean_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv")
        final_bioo_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(
            output_path,
            f"{file_prefix}_delta_diaa_mean_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv")
        final_delta_diaa_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        output_file = os.path.join(
            output_path,
            f"{file_prefix}_delta_bioo_mean_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv")
        final_delta_bioo_mean.to_csv(output_file, index=False)
        logger.info(f"已保存文件: {output_file}")

        # 简化绘图逻辑 - Draw plot based on mean data
        # Use the delta_bioo_mean dataframe for plotting AABI
        plot_mean_df = dataframes.get('delta_bioo_mean', None)
        
        if plot_mean_df is not None and not plot_mean_df.empty:
            if times > 0 and len(random_values) > 1:
                logger.info("Plotting mean AABI for each simulation.")
                # Find all mean columns for delta_bioo simulations
                sim_mean_cols = [col for col in plot_mean_df.columns if col.startswith('mean_delta_bioo_')]
                
                if sim_mean_cols:
                    for mean_col in sim_mean_cols:
                        # Extract rand_val from column name (e.g., mean_delta_bioo_0.123 -> 0.123)
                        try:
                            rand_val_str = mean_col.split('_')[-1]
                            # Plot this simulation's mean
                            pyplot.plot(
                                plot_mean_df['Year'],
                                plot_mean_df[mean_col],
                                label=f"{mm}_rand_{rand_val_str}")
                            logger.info(f"Plotted AABI curve for simulation {rand_val_str}")
                        except IndexError:
                            logger.warning(f"Could not parse random value from column name: {mean_col}")
                            # Fallback: plot with the raw column name as label
                            pyplot.plot(plot_mean_df['Year'], plot_mean_df[mean_col], label=f"{mm}_{mean_col}")
                else:
                    logger.warning("No simulation-specific mean columns found in delta_bioo_mean for plotting.")
                    # Fallback: Plot the first available non-Year, non-samp.depth column if any
                    fallback_cols = [col for col in plot_mean_df.columns if col not in ['Year', 'samp.depth']]
                    if fallback_cols:
                         pyplot.plot(plot_mean_df['Year'], plot_mean_df[fallback_cols[0]], label=f"{mm}_mean")
                         logger.info(f"Plotted fallback AABI curve using column: {fallback_cols[0]}")
                         
            else:
                # Original logic: Plot the single mean column (e.g., 'mean_delta_bioo')
                logger.info("Plotting single overall mean AABI curve.")
                mean_col_name = 'mean_delta_bioo'
                if mean_col_name in plot_mean_df.columns:
                    pyplot.plot(plot_mean_df['Year'], plot_mean_df[mean_col_name], label=mm)
                    logger.info(f"Plotted overall AABI curve using column: {mean_col_name}")
                else:
                    # Fallback if 'mean_delta_bioo' column doesn't exist (shouldn't happen in this case)
                    fallback_cols = [col for col in plot_mean_df.columns if col not in ['Year', 'samp.depth']]
                    if fallback_cols:
                         pyplot.plot(plot_mean_df['Year'], plot_mean_df[fallback_cols[0]], label=f"{mm}_mean")
                         logger.info(f"Plotted fallback AABI curve using column: {fallback_cols[0]}")
        else:
             logger.warning("Could not find or plot delta_bioo_mean data.")

        # 设置图表标签和图例
        pyplot.legend(loc='upper left')
        pyplot.ylabel('AABI (kgC $tree^{-1} year^{-1}$)')
        pyplot.xlabel('year')
        pyplot.title(f"Site: {mm} (ID: {site_id})")

        # 保存和显示当前站点图表
        plot_file = os.path.join(output_path, f"delta_bio_plot_{site_id}_{region}_{species}_{mm}.png")
        pyplot.savefig(plot_file, dpi=300)
        logger.info(f"已保存绘图: {plot_file}")
        pyplot.show(block=False)  # Use non-blocking to allow multiple windows

        # 记录处理时间
        processed_files += 1
        file_elapsed = time.time() - file_start_time
        overall_elapsed = time.time() - start_time
        avg_time_per_file = overall_elapsed / processed_files
        est_remaining = avg_time_per_file * (total_files - processed_files)

        logger.info(f"文件 {mm} 处理完成, 耗时: {file_elapsed:.2f}秒")
        logger.info(f"总进度: {processed_files}/{total_files}, 预计剩余时间: {est_remaining:.2f}秒")

    logger.info(f"所有文件处理完成, 总耗时: {time.time() - start_time:.2f}秒")

    # 显示完成提示
    total_time = time.time() - start_time
    msg = f"处理完成!\n总共处理了 {processed_files} 个文件\n总耗时: {total_time:.2f}秒"
    try:
        # 尝试使用tkinter显示消息框
        messagebox.showinfo("处理完成", msg)
    except Exception as e:
        # 如果失败，则使用控制台输出
        print("\n" + "=" * 50)
        print(msg)
        print("=" * 50 + "\n")

    pyplot.show()  # Ensure all plots are shown at the end
    return
