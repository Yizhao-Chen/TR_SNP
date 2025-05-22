import csv
import random
import pandas as pd
import numpy as np
import os
import logging
from matplotlib import pyplot
import rpy2.robjects
from rpy2.robjects import r, pandas2ri
from rpy2.robjects.conversion import localconverter
from rpy2.robjects.packages import importr
from improved_allodb import batch_estimate_biomass

# Activate pandas R object conversion
pandas2ri.activate()

METADATA_CACHE = {} # Global cache for tree metadata  # 全局缓存，用于存储元数据以避免重复IO操作
# Import necessary R packages
dplR = importr('dplR')
r_base = importr('base')

def get_metadata_for_tree(tree_name, metadata_file="metadata.csv"):
    """获取树木元数据（树种代码和坐标信息）"""
    species_code = "PIST"  # 默认树种代码
    lat = None
    lon = None
    
    try:
        # If metadata file is not provided or empty, just return defaults
        if not metadata_file:
            print(f"No metadata file provided, using default values for {tree_name}")
            return species_code, lat, lon
            
        mf = metadata_file  # 使用传入的元数据文件
        print(f"Attempting to read metadata from: {mf}")
        
        # 从缓存中查找
        if tree_name in METADATA_CACHE:
            species_code, lat, lon = METADATA_CACHE[tree_name]
            print(f"Found cached metadata: lat={lat}, lon={lon}, species_code={species_code}")
        else:
            # 如果缓存中没有，进行一次性查找并添加到缓存
            if os.path.isfile(mf):
                print(f"Metadata file exists: {mf}")
                
                # 检查文件是否有内容
                file_size = os.path.getsize(mf)
                print(f"Metadata file size: {file_size} bytes")
                
                with open(mf) as f:
                    reader = csv.DictReader(f)
                    # Get the field/column names
                    fieldnames = reader.fieldnames
                    print(f"Metadata CSV columns: {fieldnames}")
                    
                    # 先检查 'site_id' 列是否存在
                    if 'site_id' not in fieldnames:
                        print(f"ERROR: 'site_id' column not found in metadata file. Available columns: {fieldnames}")
                        METADATA_CACHE[tree_name] = (species_code, lat, lon)
                        return species_code, lat, lon
                    
                    # 重新打开文件以读取数据
                    f.seek(0)
                    reader = csv.DictReader(f)
                    
                    # 打印前几行数据用于调试
                    print(f"Looking for site_id: {tree_name}")
                    rows_checked = 0
                    for row in reader:
                        rows_checked += 1
                        if rows_checked <= 3:  # 仅打印前3行
                            print(f"Row {rows_checked}: site_id={row.get('site_id', 'N/A')}")
                        
                        if row.get('site_id') == tree_name:
                            species_code = row.get('tree_species_code', species_code)
                            if 'latitude' in row and 'longitude' in row:
                                try:
                                    lat = float(row['latitude'])
                                    lon = float(row['longitude'])
                                except (ValueError, TypeError):
                                    print(f"Warning: Could not convert lat/lon to float: lat={row['latitude']}, lon={row['longitude']}")
                                    pass
                            print(f"Found metadata: lat={lat}, lon={lon}, species_code={species_code}")
                            # 添加到缓存
                            METADATA_CACHE[tree_name] = (species_code, lat, lon)
                            break
                    else:
                        # 如果在文件中没有找到，使用默认值并添加到缓存
                        print(f"Site ID '{tree_name}' not found in metadata file after checking {rows_checked} rows")
                        # 检查是否有.rwl扩展名
                        if tree_name.endswith('.rwl'):
                            # 尝试去掉.rwl再查找
                            base_name = tree_name[:-4]
                            print(f"Retrying search with base name: {base_name}")
                            
                            # 重新打开文件
                            f.seek(0)
                            reader = csv.DictReader(f)
                            for row in reader:
                                if row.get('site_id') == base_name:
                                    species_code = row.get('tree_species_code', species_code)
                                    if 'latitude' in row and 'longitude' in row:
                                        try:
                                            lat = float(row['latitude'])
                                            lon = float(row['longitude'])
                                        except (ValueError, TypeError):
                                            pass
                                    print(f"Found metadata using base name: lat={lat}, lon={lon}, species_code={species_code}")
                                    # 添加到缓存
                                    METADATA_CACHE[tree_name] = (species_code, lat, lon)
                                    break
                            else:
                                print(f"Base name '{base_name}' not found either, using default values species_code={species_code}")
                                METADATA_CACHE[tree_name] = (species_code, lat, lon)
                        else:
                            METADATA_CACHE[tree_name] = (species_code, lat, lon)
            else:
                # 文件不存在，使用默认值并添加到缓存
                print(f"Metadata file does not exist at: {mf}")
                METADATA_CACHE[tree_name] = (species_code, lat, lon)
    except Exception as e:
        print(f"Error reading metadata file: {e}")
        import traceback
        traceback.print_exc()
    
    return species_code, lat, lon

# Add the process_tree_data function (copied from plot_all_allometry_species.py)
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
                # Simplify to just samp.depth_<rand_val> or samp.depth
                if '_' in var_type: # Check if it contains random value suffix
                    rand_val_suffix = var_type.split('_')[-1]
                    samp_depth_col_name = f"samp.depth_{rand_val_suffix}"
                else:
                    samp_depth_col_name = "samp.depth" # Standard name for single simulation
                
                # Use R-returned years if no original years provided, or align otherwise
                if orig_dataframe is not None and years is not None:
                    # Align lengths if necessary
                    if len(year) <= len(years):
                        # Use the beginning part of original years
                        result_df = pd.DataFrame({
                            'Year': years[:len(year)],
                            mean_col_name: mean_val,
                            samp_depth_col_name: samp_depth_val
                        })
                    else:
                        # Truncate R results to match original years length
                        result_df = pd.DataFrame({
                            'Year': years,
                            mean_col_name: mean_val[:len(years)],
                            samp_depth_col_name: samp_depth_val[:len(years)]
                        })
                else:
                    # Use R's years directly
                    result_df = pd.DataFrame({
                        'Year': year,
                        mean_col_name: mean_val,
                        samp_depth_col_name: samp_depth_val
                    })

                return result_df
        else:
            # 已经是pandas DataFrame, assume correct columns and return
            return r_result

    except Exception as e:
        print(f"Error in R-Python conversion: {str(e)}")
        # Fallback to simple pandas calculation if possible
        if orig_dataframe is not None and years is not None:
            mean_col_name = f"mean_{var_type}"
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
            print("Warning: Not enough information for fallback calculation during R-Python conversion error.")
            return pd.DataFrame() # Return empty DataFrame

# 生成随机值列表 - 修复的代码
def generate_random_values(min_value, max_value, times):
    '''生成随机值列表，使用集合保证唯一性，优化版本'''
    if times <= 0:
        return [0 if times == 0 else min_value]  # 简化逻辑
        
    # 使用numpy生成随机值，比random更高效
    import numpy as np
    # 生成一批足够多的随机值以确保有足够的唯一值
    batch_size = min(times * 3, 1000)  # 避免生成过多值
    random_values = set()
    
    while len(random_values) < times:
        new_values = np.round(np.random.uniform(min_value, max_value, batch_size), 3)
        random_values.update(new_values)
        # 如果生成了足够多的值，截断并返回
        if len(random_values) >= times:
            random_values_list = list(random_values)[:times]
            print(f"Generated {len(random_values_list)} unique random values")
            return random_values_list
            
    # 这里应该不会到达，但为安全起见
    return list(random_values)[:times]  # 对于无校正模式，返回0

# Add memoization decorator for expensive functions
def memoize(func):
    cache = {}
    def wrapper(*args):
        key = str(args)
        if key not in cache:
            cache[key] = func(*args)
        return cache[key]
    return wrapper

# 批量计算生物量的函数
def calculate_biomass_batch(diameter_values, species_code, lat, lon, logger=None):
    '''
    批量计算树木生物量，对多个直径值同时应用同一个生物量方程
    
    参数:
        diameter_values: 直径值列表或单个直径值
        species_code: 物种代码
        lat, lon: 纬度和经度
        
    返回:
        numpy数组，包含每个直径值对应的生物量
    '''
    try:
        # 确保diameter_values是可迭代的
        if not isinstance(diameter_values, (list, np.ndarray)):
            if logger:
                logger.warning(f"diameter_values不是列表或数组类型: {type(diameter_values)}")
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
        from species_mapper import SPECIES_CODE_MAP
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

        results = batch_estimate_biomass([diameter_values], latin_name, coords=coords)

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
                    logger.warning(f"结果长度 ({len(results[0]['agb'])}) 与输入长度 ({len(diameter_values)}) 不匹配")

                # 填充结果到正确长度
                output_values = np.full(len(diameter_values), np.nan)
                min_len = min(len(results[0]['agb']), len(diameter_values))
                output_values[:min_len] = results[0]['agb'].values[:min_len]
                return output_values

            return results[0]['agb'].values

        # 如果批处理失败，退回到逐一计算
        if logger:
            logger.warning("批量计算结果为空，回退到逐一计算")
            
        biomass_values = []
        for dbh in diameter_values:
            try:
                from allometric_dict import allometric_dict
                biomass = allometric_dict(dbh, species_code, lat, lon, logger)
                biomass_values.append(biomass)
            except Exception as e:
                if logger:
                    logger.error(f"计算单个生物量时出错: dbh={dbh}, error={e}")
                biomass_values.append(np.nan)

        return np.array(biomass_values)
        
    except Exception as e:
        error_msg = f"批量计算生物量出错: {e}"
        if logger:
            logger.error(error_msg, exc_info=True)
        else:
            print(error_msg)
            
        # 退回到逐一计算
        biomass_values = []
        for dbh in diameter_values:
            try:
                from allometric_dict import allometric_dict
                biomass = allometric_dict(dbh, species_code, lat, lon, logger)
                biomass_values.append(biomass)
            except Exception as e2:
                if logger:
                    logger.error(f"计算单个生物量时出错: dbh={dbh}, error={e2}")
                biomass_values.append(np.nan)

        return np.array(biomass_values)

# Add memoization for expensive functions
biomass_cache = {}

def cached_calculate_biomass_batch(diameter_values, species_code, lat, lon, logger=None):
    '''
    Cached version of calculate_biomass_batch that stores results to avoid redundant calculations
    '''
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

# 处理单个树木列的代码 - 修复后的函数
def process_tree_column(pdf_sub, first_valid_idx, rand_val, dbh_method, species_code, lat, lon, logger=None, file_Column_Randoms=None, col_idx=None, times=0, bark_method=0, region=None, user_geometric_rate=1.0, user_bark_rate=0.05):
    """处理单个树木列的数据，计算直径和生物量
    
    参数说明:
    - pdf_sub: 单个树木样本的数据
    - first_valid_idx: 第一个有效值的索引
    - rand_val: 随机值
    - dbh_method: 树干直径校正方法
        - -1: 不校正
        - 0: Lockwood et al.,2021方程
        - 1: 用户自定义校正率
    - bark_method: 树皮处理方法
        - -1: 自定义处理 (Custom)
        - 0: 不处理树皮 (No)
        - 1: 基于生物计量学处理 (Allometry)
    - species_code: 树种代码
    - lat, lon: 坐标
    - logger: 日志记录器
    - file_Column_Randoms: 自定义初始宽度偏差列表
    - col_idx: 列索引
    - times: 随机值次数
    - region: 地区
    - user_geometric_rate: 用户定义的几何校正率
    - user_bark_rate: 用户定义的树皮校正率
    """
    # 获取开始和结束索引
    y_start = first_valid_idx
    y_end = pdf_sub.last_valid_index()
    
    if y_start is None or y_end is None:
        return None, None, None, None, None, None, None, None, None
    
    # 初始化向量
    diameter = pd.Series(np.nan, index=pdf_sub.index)
    diameterr = pd.Series(np.nan, index=pdf_sub.index)
    diameterr_geo = pd.Series(np.nan, index=pdf_sub.index)
    diameterr_geo_bark = pd.Series(np.nan, index=pdf_sub.index)
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
    if times < 0 and file_Column_Randoms is not None and col_idx is not None and col_idx < len(file_Column_Randoms):
        # 只对校正后的数据应用初始宽度偏差
        pdf_sub_corrected[y_start] = pdf_sub_corrected[y_start] + file_Column_Randoms[col_idx]
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
        # No correction
        diameterr_geo[y_start] = diameterr[y_start]
    elif dbh_method == 0:
        # Lockwood et al.,2021方程
        diameterr_geo[y_start] = diameterr[y_start] * 0.998 + 22.3
    elif dbh_method == 1:
        # user defined correction rate
        diameterr_geo[y_start] = diameterr[y_start] * user_geometric_rate
        if logger:
            logger.debug(f"Geometric correction - Original diameter: {diameterr[y_start]:.4f} cm, Rate: {user_geometric_rate}, Corrected: {diameterr_geo[y_start]:.4f} cm")

    # bark correction
    if bark_method == -1:
        # Custom bark thickness based on user-defined rate
        bark_thickness = diameterr_geo[y_start] * user_bark_rate
        diameterr_geo_bark[y_start] = diameterr_geo[y_start] + bark_thickness
        if logger and y_start % 20 == 0:
            logger.debug(f"Year {y_start} custom bark correction - Original diameter: {diameterr_geo[y_start]:.4f} cm, Rate: {user_bark_rate}, Bark thickness: {bark_thickness:.4f} cm, Corrected: {diameterr_geo_bark[y_start]:.4f} cm")
    elif bark_method == 0:
        # No bark correction
        diameterr_geo_bark[y_start] = diameterr_geo[y_start]
    elif bark_method == 1:
        # Allometry-based bark correction using bark_dict_species function
        from bark_dict_species import bark_dict_species
        bark_thickness = bark_dict_species(region, species_code, diameterr_geo[y_start])
        if logger and y_start % 20 == 0:
            logger.debug(f"Year {y_start} bark correction - Species: {species_code}, Original diameter: {diameterr_geo[y_start]:.4f} cm, Bark thickness: {bark_thickness:.4f} cm, Corrected: {diameterr_geo[y_start] + bark_thickness:.4f} cm")
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
        if not pd.isna(age[k-1]):
            age[k] = age[k-1] + 1
            
        # 计算原始直径 (无校正)
        diameter[k] = diameter[k-1] + (2 * pdf_sub[k]) / 10
            
        # 计算校正后的直径 (应用了初始宽度校正)
        diameterr[k] = diameterr[k-1] + (2 * pdf_sub_corrected[k]) / 10
    
        # geometric correction
        if dbh_method == -1:
            diameterr_geo[k] = diameterr[k]
        elif dbh_method == 0:
            # Lockwood et al.,2021方程
            diameterr_geo[k] = diameterr[k] * 0.998 + 22.3
        elif dbh_method == 1:
            # user defined correction rate
            diameterr_geo[k] = diameterr[k] * user_geometric_rate

        # bark correction
        if bark_method == -1:
            # Custom bark thickness based on user-defined rate
            bark_thickness = diameterr_geo[k] * user_bark_rate
            diameterr_geo_bark[k] = diameterr_geo[k] + bark_thickness
            if logger and k % 20 == 0:
                logger.debug(f"Year {k} custom bark correction - Original diameter: {diameterr_geo[k]:.4f} cm, Rate: {user_bark_rate}, Bark thickness: {bark_thickness:.4f} cm, Corrected: {diameterr_geo_bark[k]:.4f} cm")
        elif bark_method == 0:
            # No bark correction
            diameterr_geo_bark[k] = diameterr_geo[k]
        elif bark_method == 1:
            # Allometry-based bark correction using bark_dict_species function
            from bark_dict_species import bark_dict_species
            bark_thickness = bark_dict_species(region, species_code, diameterr_geo[k])
            if logger and k % 20 == 0:
                logger.debug(f"Year {k} bark correction - Species: {species_code}, Original diameter: {diameterr_geo[k]:.4f} cm, Bark thickness: {bark_thickness:.4f} cm, Corrected: {diameterr_geo[k] + bark_thickness:.4f} cm")
            diameterr_geo_bark[k] = diameterr_geo[k] + bark_thickness
    
    # 计算直径增量
    delta_dia[y_start] = diameter[y_start]
    delta_diaa[y_start] = diameterr_geo_bark[y_start]
    
    # 计算后续年份的直径增量
    for k in range(y_start + 1, y_end + 1):
        if not pd.isna(diameter[k]) and not pd.isna(diameter[k-1]):
            delta_dia[k] = diameter[k] - diameter[k-1]
        if not pd.isna(diameterr_geo_bark[k]) and not pd.isna(diameterr_geo_bark[k-1]):
            delta_diaa[k] = diameterr_geo_bark[k] - diameterr_geo_bark[k-1]
    
    # 批量计算生物量
    valid_indices = ~diameter.isna()
    valid_diameters = diameter[valid_indices].values
    
    if len(valid_diameters) > 0:
        try:
            biomass_values = cached_calculate_biomass_batch(valid_diameters, species_code, lat, lon, logger)
            
            # 检查长度是否匹配
            if len(biomass_values) == sum(valid_indices):
                biomass[valid_indices] = biomass_values
            else:
                if logger:
                    logger.error(f"生物量计算结果长度不匹配: 预期 {sum(valid_indices)}, 实际 {len(biomass_values)}")
                # 回退到逐个赋值以避免长度不匹配错误
                valid_idx_positions = np.where(valid_indices)[0]
                for j, pos in enumerate(valid_idx_positions):
                    if j < len(biomass_values):
                        biomass.iloc[pos] = biomass_values[j]
        except Exception as e:
            if logger:
                logger.error(f"计算生物量时出错: {str(e)}")
    
    valid_indices = ~diameterr_geo_bark.isna()
    valid_diameters = diameterr_geo_bark[valid_indices].values
    
    if len(valid_diameters) > 0:
        try:
            biomasss_values = cached_calculate_biomass_batch(valid_diameters, species_code, lat, lon, logger)
            
            # 检查长度是否匹配
            if len(biomasss_values) == sum(valid_indices):
                biomasss[valid_indices] = biomasss_values
            else:
                if logger:
                    logger.error(f"校正生物量计算结果长度不匹配: 预期 {sum(valid_indices)}, 实际 {len(biomasss_values)}")
                # 回退到逐个赋值以避免长度不匹配错误
                valid_idx_positions = np.where(valid_indices)[0]
                for j, pos in enumerate(valid_idx_positions):
                    if j < len(biomasss_values):
                        biomasss.iloc[pos] = biomasss_values[j]
        except Exception as e:
            if logger:
                logger.error(f"计算校正生物量时出错: {str(e)}")
    
    # 计算生物量增量
    delta_bio[y_start] = biomass[y_start]
    delta_bioo[y_start] = biomasss[y_start]
    
    # 计算后续年份的生物量增量 - 使用向量化操作
    # 构建移位数据
    shifted_biomass = biomass.shift(1)
    shifted_biomasss = biomasss.shift(1)
    
    # 计算差值 - 向量化操作
    valid_mask = ~biomass.isna() & ~shifted_biomass.isna()
    delta_bio[valid_mask] = biomass[valid_mask] - shifted_biomass[valid_mask]
    
    valid_mask = ~biomasss.isna() & ~shifted_biomasss.isna()
    delta_bioo[valid_mask] = biomasss[valid_mask] - shifted_biomasss[valid_mask]
    
    return diameter, diameterr, diameterr_geo, diameterr_geo_bark, biomass, biomasss, delta_dia, delta_diaa, delta_bio, delta_bioo, age

# 设置显示图表的代码块 - 固定缩进问题
def display_plot(processed_files, plot_file, logger):
    """显示和保存图表的函数"""
    # 只有当至少处理了一个文件时才显示图表
    if processed_files > 0:
        # 保存图表
        pyplot.savefig(plot_file, dpi=300)
        logger.info(f"已保存绘图: {plot_file}")
        # 显示图表
        pyplot.show(block=False)  # Changed to non-blocking to allow multiple windows
    else:
        logger.warning("没有处理任何文件，跳过绘图")
        pyplot.close()

def plot_allometry(fk, min_value, max_value, times, file_Column_Randoms, 
                dbh_method, bark_method, output_path, metadata_file="metadata.csv",
                geometric_correction_rates=None, bark_correction_rates=None,
                default_geometric_rate=1.0, default_bark_rate=0.05):
    """
    处理树木生物量计算和绘图
    
    参数说明:
    - fk: 文件列表
    - min_value, max_value: 随机值范围
    - times: 随机次数
    - file_Column_Randoms: 自定义初始宽度偏差列表
    - dbh_method: 树干直径校正方法
        - -1: 不校正
        - 0: Lockwood et al.,2021方程
        - 1: 用户自定义校正率
    - bark_method: 树皮处理方法
        - -1: 自定义处理 (Custom)
        - 0: 不处理树皮 (No)
        - 1: 基于生物计量学处理 (Allometry)
    - output_path: 输出路径
    - metadata_file: 元数据文件路径
    - geometric_correction_rates: 每个文件的每个样本的几何校正率字典列表
    - bark_correction_rates: 每个文件的每个样本的树皮校正率字典列表
    - default_geometric_rate: 默认几何校正率
    - default_bark_rate: 默认树皮校正率
    """
    import logging
    import os
    import time
    from matplotlib import pyplot
    
    start_time = time.time()
    print(f"Correction Value:", min_value, max_value, times)
    print(f"dbh_method: {dbh_method}")
    print(f"bark_method: {bark_method}")
    print(f"output_path: {output_path}")
    print(f"metadata_file: {metadata_file}")
    
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
    logger.info(f"Metadata file: {metadata_file}")
    # Log the geometric correction rates
    logger.info("=== GEOMETRIC CORRECTION RATES ===")
    if geometric_correction_rates:
        for idx, rates in enumerate(geometric_correction_rates):
            if rates:
                logger.info(f"File #{idx}: {type(rates)}, {len(rates)} rate entries")
                if isinstance(rates, dict) and len(rates) > 0:
                    sample_items = list(rates.items())[:min(5, len(rates))]
                    logger.info(f"Sample entries: {sample_items}")
            else:
                logger.info(f"File #{idx}: No rates defined")
    else:
        logger.info("No geometric correction rates defined")
    logger.info("=======================================")

    # Initialize correction rates if not provided and ensure they are lists of dicts
    if geometric_correction_rates is None or not isinstance(geometric_correction_rates, list):
        geometric_correction_rates = [{} for _ in fk]
    else:
        # Ensure each element is a dictionary
        geometric_correction_rates = [rates if isinstance(rates, dict) else {} for rates in geometric_correction_rates]
        
    if bark_correction_rates is None or not isinstance(bark_correction_rates, list):
        bark_correction_rates = [{} for _ in fk]
    else:
        # Ensure each element is a dictionary
        bark_correction_rates = [rates if isinstance(rates, dict) else {} for rates in bark_correction_rates]
    
    pyplot.rcParams['savefig.dpi'] = 300
    pyplot.rcParams['figure.dpi'] = 300
    
    # Remove global figure initialization - we'll create per-site figures
    # pyplot.figure() 
    
    # 记录处理时间和总文件数，用于估算剩余时间
    total_files = len(fk)
    processed_files = 0
    
    # 导入必要的R交互模块 - 优化：只导入一次，避免每个文件都重复导入
    from rpy2.robjects import r, pandas2ri
    from rpy2.robjects.packages import importr
    from rpy2.robjects.conversion import localconverter
    import rpy2.robjects
    
    # 导入并激活dplR包 - 优化：只激活一次
    # Moved import dplR to top level
    # Moved pandas2ri.activate() to top level
    
    for indexF in range(len(fk)):
        # Create a new figure for each site
        pyplot.figure()
        
        file_start_time = time.time()
        tree_file = fk[indexF]
        
        # 获取文件名（不含路径和扩展名）
        import os
        mm = os.path.splitext(os.path.basename(tree_file))[0]
        
        # 获取树木元数据 - 传入用户选择的元数据文件
        species_code, lat, lon = get_metadata_for_tree(mm, metadata_file)
        
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
        
        logger.info(f"Using random values: {random_values}")
        
        # 读取树木年轮宽度数据
        import pandas as pd
        import numpy as np
        try:
            # 读取树木年轮数据
            logger.info(f"读取树木文件: {tree_file}")
            TR_input = r['read.tucson'](tree_file)
            start = r['min'](r['as.numeric'](r['rownames'](TR_input)))
            end = r['max'](r['as.numeric'](r['rownames'](TR_input)))
            
            # 显示一些基本信息，便于调试
            num_samples = len(r['colnames'](TR_input))
            logger.info(f"文件包含 {num_samples} 个样本，年份范围: {start[0]} - {end[0]}")
            
            # 优化: 一次性获取年份范围并转换R数据框为pandas
            with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
                t_start = float(start[0])
                t_end = float(end[0])
                years = range(int(t_start), int(t_end) + 1)
                
                # 一次性转换 R 数据框为 pandas，并直接设置年份为索引
                pdf_input = pandas2ri.rpy2py(TR_input)
                pdf_input.index = years
                pdf_input.insert(0, "Year", years)
                
                # 记录原始数据的一些统计信息
                logger.info(f"转换后DataFrame形状: {pdf_input.shape}")
                logger.info(f"DataFrame列名: {list(pdf_input.columns)}")
            
            # 记录每列的第一个非空值索引，优化后续计算
            first_valid_indices = {}
            for i, col in enumerate(pdf_input.columns):
                if col == 'Year':
                    continue  # 跳过Year列
                first_valid_indices[i] = pdf_input[col].first_valid_index()
                if first_valid_indices[i] is not None:
                    logger.info(f"样本 {col} 的第一个非空值在年份 {first_valid_indices[i]}")
                else:
                    logger.warning(f"样本 {col} 没有有效值")
                
            logger.info(f"成功读取树木宽度数据: {len(years)} 年, {len(pdf_input.columns)-1} 个样本")
                
            # 创建诊断文件来跟踪处理过程
            diagnostic_file = os.path.join(output_path, f"{mm}_processing_diagnostic.txt")
            with open(diagnostic_file, 'w') as f:
                f.write(f"Processing file: {tree_file}\n")
                f.write(f"Species code: {species_code}\n")
                f.write(f"Random values: {random_values}\n")
                f.write(f"Years range: {min(years)} - {max(years)}, Total years: {len(years)}\n")
                f.write(f"DataFrame columns: {list(pdf_input.columns)}\n\n")
                
                # 示例数据信息
                for col in pdf_input.columns:
                    if col == 'Year':
                        continue
                    valid_values = pdf_input[col].dropna().values
                    if len(valid_values) > 0:
                        f.write(f"Sample: {col}\n")
                        f.write(f"  Valid values: {len(valid_values)}\n")
                        f.write(f"  First few values: {valid_values[:5]}\n")
                        first_idx = pdf_input[col].first_valid_index()
                        if first_idx is not None:
                            f.write(f"  First valid index: {first_idx}\n")
                    else:
                        f.write(f"Sample {col}: No valid values\n")
                    f.write("\n")
            
            logger.info(f"已保存处理诊断文件: {diagnostic_file}")
                
            # 优化: 使用数据字典来收集数据，避免频繁创建/修改DataFrame
            data_columns = {
                'dia': {'Year': years},
                'bio': {'Year': years},
                'delta_dia': {'Year': years},
                'delta_bio': {'Year': years},
                'diaa': {'Year': years},
                'bioo': {'Year': years},
                'delta_diaa': {'Year': years}, 
                'delta_bioo': {'Year': years},
                'age': {'Year': years},
                'dia_mean': {'Year': years},
                'bio_mean': {'Year': years},
                'delta_dia_mean': {'Year': years},
                'delta_bio_mean': {'Year': years},
                'diaa_mean': {'Year': years},
                'bioo_mean': {'Year': years},
                'delta_diaa_mean': {'Year': years},
                'delta_bioo_mean': {'Year': years},
                'age_mean': {'Year': years}
            }
            
            # 处理每个样本和随机值
            for rand_val in random_values:
                logger.info(f"Processing random value: {rand_val}")
                
                for i, col in enumerate(pdf_input.columns):
                    if col == 'Year':
                        continue
                    
                    # 获取样本数据，优化：直接使用pandas Series
                    pdf_sub = pdf_input[col].copy()
                    
                    # 检查是否有有效的第一个索引
                    y_start = pdf_sub.first_valid_index()
                    if y_start is None:
                        logger.warning(f"列 {col} 没有有效值，跳过处理")
                        continue
                    
                    # 使用 process_tree_column 处理数据
                    # Get sample name (column name in the dataframe)
                    column_name = pdf_input.columns[i]

                    # Default rates
                    user_geometric_rate = default_geometric_rate
                    user_bark_rate = default_bark_rate
                    region = "default" # Region might not be relevant here, use default

                    # Look up geometric correction rate by sample name if available
                    if geometric_correction_rates and indexF < len(geometric_correction_rates) and isinstance(geometric_correction_rates[indexF], dict):
                        if column_name in geometric_correction_rates[indexF]:
                            user_geometric_rate = geometric_correction_rates[indexF][column_name]
                            logger.info(f"Applied custom geometric rate for sample {column_name}: {user_geometric_rate}")
                        elif i in geometric_correction_rates[indexF]: # Fallback to index
                            user_geometric_rate = geometric_correction_rates[indexF][i]
                            logger.info(f"Applied index-based geometric rate for sample {column_name}: {user_geometric_rate}")
                    else:
                         logger.info(f"Using default geometric rate for sample {column_name}: {user_geometric_rate}")

                    # Look up bark correction rate by sample name if available
                    if bark_correction_rates and indexF < len(bark_correction_rates) and isinstance(bark_correction_rates[indexF], dict):
                        if column_name in bark_correction_rates[indexF]:
                            user_bark_rate = bark_correction_rates[indexF][column_name]
                            logger.info(f"Using custom bark rate for sample {column_name}: {user_bark_rate}")
                        elif i in bark_correction_rates[indexF]: # Fallback to index
                            user_bark_rate = bark_correction_rates[indexF][i]
                            logger.info(f"Using index-based bark rate for sample {column_name}: {user_bark_rate}")
                    else:
                        logger.info(f"Using default bark rate for sample {column_name}: {user_bark_rate}")
                    
                    # 记录传递给process_tree_column的关键参数
                    logger.info(f"处理样本 {col} 的随机值 {rand_val}, 第一个有效索引对应年份: {y_start}")
                    
                    # Pass the specific list for the current file
                    current_file_biases = file_Column_Randoms[indexF] if file_Column_Randoms and indexF < len(file_Column_Randoms) else []
                    
                    diameter, diameterr, diameterr_geo, diameterr_geo_bark, biomass, biomasss, delta_dia, delta_diaa, delta_bio, delta_bioo, age = process_tree_column(
                        pdf_sub, y_start, rand_val, dbh_method, species_code, lat, lon, 
                        logger, current_file_biases, i, times, bark_method, region, 
                        user_geometric_rate, user_bark_rate
                    )
                    
                    if diameter is None:
                        continue
                    
                    # 修正：为列名添加随机值标识，确保当times>0时每个随机值都有唯一的列名
                    if times > 0:
                        # 使用随机值作为列名的一部分，确保每个随机值都有唯一的列名
                        column_suffix = f"{rand_val}_{col}"
                    else:
                        column_suffix = col
                    
                    # 输出当前处理的随机值和列名以便调试
                    logger.info(f"Adding columns with random value {rand_val} for sample {col}, using column suffix: {column_suffix}")
                    
                    # 添加到结果数据字典
                    col_key = f"dia_{column_suffix}"
                    data_columns['dia'][col_key] = diameter
                    
                    col_key = f"bio_{column_suffix}"
                    data_columns['bio'][col_key] = biomass
                    
                    col_key = f"delta_dia_{column_suffix}"
                    data_columns['delta_dia'][col_key] = delta_dia
                    
                    col_key = f"delta_bio_{column_suffix}"
                    data_columns['delta_bio'][col_key] = delta_bio
                    
                    col_key = f"diaa_{column_suffix}"
                    data_columns['diaa'][col_key] = diameterr_geo_bark
                    
                    col_key = f"bioo_{column_suffix}"
                    data_columns['bioo'][col_key] = biomasss
                    
                    col_key = f"delta_diaa_{column_suffix}"
                    data_columns['delta_diaa'][col_key] = delta_diaa
                    
                    col_key = f"delta_bioo_{column_suffix}"
                    data_columns['delta_bioo'][col_key] = delta_bioo
                    
                    col_key = f"age_{column_suffix}"
                    data_columns['age'][col_key] = age
            
            # 优化: 一次性创建DataFrame，避免频繁修改
            dataframes = {}
            for key in ['dia', 'bio', 'delta_dia', 'delta_bio', 'diaa', 'bioo', 'delta_diaa', 'delta_bioo', 'age']:
                dataframes[key] = pd.DataFrame(data_columns[key])
            
            dia_all = dataframes['dia']
            bio_all = dataframes['bio']
            delta_dia_all = dataframes['delta_dia']
            delta_bio_all = dataframes['delta_bio']
            diaa_all = dataframes['diaa']
            bioo_all = dataframes['bioo']
            delta_diaa_all = dataframes['delta_diaa']
            delta_bioo_all = dataframes['delta_bioo']
            age_all = dataframes['age']
            
            # 在完成所有随机值处理后，计算各个样本的均值 - ADDED MEAN CALCULATION
            logger.info("Calculating means across samples...")
            for var_type in ['dia', 'bio', 'delta_dia', 'delta_bio', 'diaa', 'bioo', 'delta_diaa', 'delta_bioo', 'age']:
                var_df = dataframes[var_type]
                all_sample_cols = [col for col in var_df.columns if col != 'Year'] 

                if not all_sample_cols:
                    logger.warning(f"No sample columns found for {var_type}")
                    dataframes[f'{var_type}_mean'] = pd.DataFrame({'Year': years}) # Store empty mean df
                    continue
                    
                mean_output_df = pd.DataFrame({'Year': years})
                
                if times > 0 and len(random_values) > 1:
                    logger.info(f"Calculating {var_type} means and sample depths for {len(random_values)} simulations.")
                    for rand_val in random_values:
                        # Corrected logic: Find columns containing the random value suffix AND sample name part
                        # This assumes column names are like 'dia_0.123_Sample1'
                        rand_suffix = f"_{rand_val}_" 
                        sim_sample_cols = [col for col in all_sample_cols if rand_suffix in col]

                        if not sim_sample_cols:
                            logger.warning(f"No sample columns found for {var_type} simulation {rand_val}")
                            continue
                        
                        logger.debug(f"Processing {var_type} mean & depth for sim {rand_val} using {len(sim_sample_cols)} columns.")
                        
                        sim_mean_col_name = f"mean_{var_type}_{rand_val}"
                        sim_samp_depth_col_name = f"samp.depth_{rand_val}"

                        try:
                            sample_data = var_df[sim_sample_cols]
                            with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
                                r_df = pandas2ri.py2rpy(sample_data)
                                r_result = dplR.chron(r_df) 
                                
                            temp_process_var_type = f"{var_type}_{rand_val}"
                            sim_mean_df_from_r = process_tree_data(r_result, sample_data, years, temp_process_var_type)
                            
                            if sim_mean_col_name in sim_mean_df_from_r.columns and sim_samp_depth_col_name in sim_mean_df_from_r.columns:
                                mean_values = sim_mean_df_from_r[sim_mean_col_name].values
                                samp_depth_values = sim_mean_df_from_r[sim_samp_depth_col_name].values
                                
                                if len(mean_values) >= len(years):
                                    mean_output_df[sim_mean_col_name] = mean_values[:len(years)]
                                else: 
                                    padded = np.full(len(years), np.nan)
                                    padded[:len(mean_values)] = mean_values
                                    mean_output_df[sim_mean_col_name] = padded
                                    
                                if len(samp_depth_values) >= len(years):
                                    mean_output_df[sim_samp_depth_col_name] = samp_depth_values[:len(years)]
                                else: 
                                    padded_sd = np.full(len(years), np.nan)
                                    padded_sd[:len(samp_depth_values)] = samp_depth_values
                                    mean_output_df[sim_samp_depth_col_name] = padded_sd
                                    
                                logger.info(f"Processed {sim_mean_col_name} and {sim_samp_depth_col_name} using R biweight mean.")
                            else:
                                 missing_cols = [c for c in [sim_mean_col_name, sim_samp_depth_col_name] if c not in sim_mean_df_from_r.columns]
                                 raise ValueError(f"Columns {missing_cols} not found in R result processing for sim {rand_val}.")

                        except Exception as e:
                            logger.warning(f"R processing failed for sim {rand_val}, falling back to pandas: {e}")
                            mean_values = var_df[sim_sample_cols].mean(axis=1).values
                            samp_depth_values = var_df[sim_sample_cols].count(axis=1).values
                            
                            if len(mean_values) >= len(years):
                                mean_output_df[sim_mean_col_name] = mean_values[:len(years)]
                            else:
                                padded = np.full(len(years), np.nan)
                                padded[:len(mean_values)] = mean_values
                                mean_output_df[sim_mean_col_name] = padded
                                
                            if len(samp_depth_values) >= len(years):
                                mean_output_df[sim_samp_depth_col_name] = samp_depth_values[:len(years)]
                            else:
                                padded_sd = np.full(len(years), np.nan)
                                padded_sd[:len(samp_depth_values)] = samp_depth_values
                                mean_output_df[sim_samp_depth_col_name] = padded_sd
                
                else:
                    # Single Simulation or times <= 0 Logic
                    logger.info(f"Calculating overall {var_type} mean and sample depth across {len(all_sample_cols)} samples.")
                    mean_col_name = f"mean_{var_type}" 
                    samp_depth_col_name = "samp.depth" # Standard name
                    
                    try:
                        sample_data = var_df[all_sample_cols]
                        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
                            r_df = pandas2ri.py2rpy(sample_data)
                            r_result = dplR.chron(r_df)
                            
                        mean_df_from_r = process_tree_data(r_result, sample_data, years, var_type)
                        
                        if mean_col_name in mean_df_from_r.columns and samp_depth_col_name in mean_df_from_r.columns:
                            mean_values = mean_df_from_r[mean_col_name].values
                            samp_depth_values = mean_df_from_r[samp_depth_col_name].values
                            
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
                                 
                            logger.info(f"Processed {mean_col_name} and {samp_depth_col_name} using R biweight mean")
                        else:
                            missing_cols = [c for c in [mean_col_name, samp_depth_col_name] if c not in mean_df_from_r.columns]
                            logger.warning(f"R result missing {missing_cols}, falling back to pandas mean/count.")
                            # Fallback
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
                        # Fallback
                        mean_values = var_df[all_sample_cols].mean(axis=1).values
                        samp_depth_values = var_df[all_sample_cols].count(axis=1).values
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
                        logger.info(f"Used pandas fallback for overall {var_type} mean/depth due to error.")

                dataframes[f'{var_type}_mean'] = mean_output_df
            # --- END OF ADDED MEAN CALCULATION ---

            # Assign final mean dataframes
            final_dia_mean = dataframes['dia_mean']
            final_bio_mean = dataframes['bio_mean']
            final_delta_dia_mean = dataframes['delta_dia_mean']
            final_delta_bio_mean = dataframes['delta_bio_mean']
            final_diaa_mean = dataframes['diaa_mean']
            final_bioo_mean = dataframes['bioo_mean']
            final_delta_diaa_mean = dataframes['delta_diaa_mean']
            final_delta_bioo_mean = dataframes['delta_bioo_mean']
            final_age_mean = dataframes['age_mean']
            
            # 在完成所有随机值处理后，输出数据框的列名以便调试
            logger.info(f"Final column count for delta_bio_all: {len(delta_bio_all.columns)}")
            if times > 0:
                # 检查是否有预期的随机值列
                has_expected_columns = False
                for col in delta_bio_all.columns:
                    if col != 'Year' and '_' in col:
                        has_expected_columns = True
                        break
                        
                if not has_expected_columns:
                    logger.error("随机值列未正确创建，可能出现了问题，请检查数据框")
                else:
                    logger.info("随机值列已成功创建")
            
            # 保存诊断信息
            if times > 0:
                # 创建诊断文件，以帮助跟踪随机值是如何应用的
                diagnostic_file = os.path.join(output_path, f"{mm}_random_value_diagnostic.txt")
                with open(diagnostic_file, 'w') as f:
                    f.write(f"Random values used: {random_values}\n\n")
                    f.write(f"Delta bio all columns: {list(delta_bio_all.columns)}\n\n")
                    
                    # 写入各个随机值的列信息
                    for rand_val in random_values:
                        # 修正查找特定随机值的列
                        random_cols = [col for col in delta_bio_all.columns if col != 'Year' and f"{rand_val}_" in col]
                        f.write(f"Columns for random value {rand_val}: {random_cols}\n")
                        
                        # 计算这个随机值的均值并添加到诊断信息中，但不创建单独的CSV文件
                        if random_cols:
                            mean_col_name = f'mean_{rand_val}'
                            delta_bio_all[mean_col_name] = delta_bio_all[random_cols].mean(axis=1)
                            f.write(f"Created mean column: {mean_col_name}\n")
                
                logger.info(f"Saved random value diagnostic to: {diagnostic_file}")
            
            # 设置各种校正选项的编码
            initial_width_code = 2 if times > 0 else 1 if times < 0 else 0
            geometric_code = 0 if dbh_method == -1 else 1 if dbh_method == 0 else 2
            bark_code = 0 if bark_method == 0 else 1 if bark_method == 1 else 2
            
            # 保存结果到文件
            file_prefix = f"{mm}"
            
            # --- START OF MODIFIED SAVING SECTION ---
            # Define correction codes
            initial_width_code = 2 if times > 0 else 1 if times < 0 else 0
            geometric_code = 0 if dbh_method == -1 else 1 if dbh_method == 0 else 2
            bark_code = 0 if bark_method == 0 else 1 if bark_method == 1 else 2

            # Save individual sample dataframes (existing code)
            # ... (Keep the existing saving block for dia_all, bio_all, etc.) ...
            # 并行保存所有文件 - 优化：使用批量保存来减少磁盘操作
            # 保存非校正文件 - 标准格式
            file_saves = [
                (os.path.join(output_path, f"{file_prefix}_dia.csv"), dia_all),
                (os.path.join(output_path, f"{file_prefix}_bio.csv"), bio_all),
                (os.path.join(output_path, f"{file_prefix}_delta_dia.csv"), delta_dia_all),
                (os.path.join(output_path, f"{file_prefix}_delta_bio.csv"), delta_bio_all),
                (os.path.join(output_path, f"{file_prefix}_age.csv"), age_all),
                # 保存校正文件 - 包含校正代码
                (os.path.join(output_path, f"{file_prefix}_diaa_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), diaa_all),
                (os.path.join(output_path, f"{file_prefix}_bioo_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), bioo_all),
                (os.path.join(output_path, f"{file_prefix}_delta_diaa_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), delta_diaa_all),
                (os.path.join(output_path, f"{file_prefix}_delta_bioo_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), delta_bioo_all),
                # ADDED: Save mean dataframes
                (os.path.join(output_path, f"{file_prefix}_dia_mean.csv"), final_dia_mean),
                (os.path.join(output_path, f"{file_prefix}_bio_mean.csv"), final_bio_mean),
                (os.path.join(output_path, f"{file_prefix}_delta_dia_mean.csv"), final_delta_dia_mean),
                (os.path.join(output_path, f"{file_prefix}_delta_bio_mean.csv"), final_delta_bio_mean),
                (os.path.join(output_path, f"{file_prefix}_age_mean.csv"), final_age_mean),
                # ADDED: Save corrected mean dataframes
                (os.path.join(output_path, f"{file_prefix}_diaa_mean_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), final_diaa_mean),
                (os.path.join(output_path, f"{file_prefix}_bioo_mean_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), final_bioo_mean),
                (os.path.join(output_path, f"{file_prefix}_delta_diaa_mean_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), final_delta_diaa_mean),
                (os.path.join(output_path, f"{file_prefix}_delta_bioo_mean_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), final_delta_bioo_mean)
            ]
            
            # 并行写入所有文件
            from concurrent.futures import ThreadPoolExecutor
            
            def save_df_to_csv(file_info):
                output_file, df = file_info
                df.to_csv(output_file, index=False)
                return output_file
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_file = {executor.submit(save_df_to_csv, file_info): file_info[0] for file_info in file_saves}
                for future in future_to_file:
                    try:
                        output_file = future.result()
                        logger.info(f"已保存文件: {output_file}")
                    except Exception as e:
                        logger.error(f"Error saving file: {e}")
            
            logger.info(f"已保存文件: {output_file}")
            
            # 绘制delta_bio曲线 - Use mean dataframe for plotting
            # Modify plotting logic to use the mean dataframe similar to species version
            if times > 0 and len(random_values) > 1:
                 logger.info("Plotting mean AABI for each simulation.")
                 # Find all mean columns for delta_bioo simulations in the mean dataframe
                 plot_mean_df = final_delta_bioo_mean # Use the calculated mean df
                 sim_mean_cols = [col for col in plot_mean_df.columns if col.startswith('mean_delta_bioo_')]
                 
                 if sim_mean_cols:
                     for mean_col in sim_mean_cols:
                         try:
                             rand_val_str = mean_col.split('_')[-1]
                             pyplot.plot(
                                 plot_mean_df['Year'],
                                 plot_mean_df[mean_col],
                                 label=f"{mm}_rand_{rand_val_str}")
                             logger.info(f"Plotted AABI curve for simulation {rand_val_str}")
                         except IndexError:
                             logger.warning(f"Could not parse random value from column name: {mean_col}")
                             pyplot.plot(plot_mean_df['Year'], plot_mean_df[mean_col], label=f"{mm}_{mean_col}")
                 else:
                     logger.warning("No simulation-specific mean columns found in delta_bioo_mean for plotting.")
                     # Fallback: Plot the first available non-Year, non-samp.depth column if any
                     fallback_cols = [col for col in plot_mean_df.columns if col not in ['Year'] and not col.startswith('samp.depth')]
                     if fallback_cols:
                         pyplot.plot(plot_mean_df['Year'], plot_mean_df[fallback_cols[0]], label=f"{mm}_mean")
                         logger.info(f"Plotted fallback AABI curve using column: {fallback_cols[0]}")
            else:
                # Original logic: Plot the single mean column (e.g., 'mean_delta_bioo')
                logger.info("Plotting single overall mean AABI curve.")
                plot_mean_df = final_delta_bioo_mean # Use the calculated mean df
                mean_col_name = 'mean_delta_bioo'
                if mean_col_name in plot_mean_df.columns:
                    pyplot.plot(plot_mean_df['Year'], plot_mean_df[mean_col_name], label=mm)
                    logger.info(f"Plotted overall AABI curve using column: {mean_col_name}")
                else:
                    # Fallback if 'mean_delta_bioo' column doesn't exist
                    fallback_cols = [col for col in plot_mean_df.columns if col not in ['Year'] and not col.startswith('samp.depth')]
                    if fallback_cols:
                         pyplot.plot(plot_mean_df['Year'], plot_mean_df[fallback_cols[0]], label=f"{mm}_mean")
                         logger.info(f"Plotted fallback AABI curve using column: {fallback_cols[0]}")
            
            # 设置当前图表的标签和图例
            pyplot.legend(loc='upper left')
            pyplot.ylabel('AABI (kgC $tree^{-1} year^{-1}$)')
            pyplot.xlabel('year')
            pyplot.title(f"Site: {mm}")
            
            # 显示和保存当前站点的图表
            plot_file = os.path.join(output_path, f"delta_bio_plot_{mm}.png")
            display_plot(1, plot_file, logger)  # Always pass 1 for processed_files to ensure display
            
        except Exception as e:
            logger.error(f"处理文件 {tree_file} 时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            pyplot.close()  # Close the figure if there was an error
        
        # 记录处理时间
        processed_files += 1
        file_elapsed = time.time() - file_start_time
        overall_elapsed = time.time() - start_time
        avg_time_per_file = overall_elapsed / processed_files
        est_remaining = avg_time_per_file * (total_files - processed_files)
        
        logger.info(f"文件 {mm} 处理完成, 耗时: {file_elapsed:.2f}秒")
        logger.info(f"总进度: {processed_files}/{total_files}, 预计剩余时间: {est_remaining:.2f}秒")
    
    # 记录总处理时间
    total_time = time.time() - start_time
    logger.info(f"所有文件处理完成, 总耗时: {total_time:.2f}秒")
    
    # 显示完成提示
    msg = f"处理完成!\n总共处理了 {processed_files} 个文件\n总耗时: {total_time:.2f}秒"
    try:
        # 尝试使用tkinter显示消息框
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        messagebox.showinfo("处理完成", msg)
        root.destroy()  # 关闭tkinter
    except Exception as e:
        # 如果失败，则使用控制台输出
        print("\n" + "="*50)
        print(msg)
        print("="*50 + "\n")
    
    pyplot.show()  # Ensure all plots are shown at the end
    return 