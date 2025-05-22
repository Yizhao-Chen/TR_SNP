import re
import os

def optimize_allometry():
    """
    Optimize plot_all_allometry.py with performance improvements similar to what we did
    for plot_all_allometry_species.py
    """
    # Create backup
    try:
        with open('plot_all_allometry.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open('plot_all_allometry.py.backup', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("Backup created: plot_all_allometry.py.backup")
    except Exception as e:
        print(f"Error creating backup: {e}")
        return
    
    # Apply optimizations:
    
    # 1. Add memoization for calculate_biomass_batch
    memoize_code = """
# Add memoization for expensive functions
_biomass_cache = {}

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
    if cache_key in _biomass_cache:
        cached_results = _biomass_cache[cache_key]
        # Check if we already calculated this exact diameter
        if diameters_tuple in cached_results:
            return cached_results[diameters_tuple]
    else:
        _biomass_cache[cache_key] = {}
    
    # Calculate the biomass
    result = calculate_biomass_batch(diameter_values, species_code, lat, lon, logger)
    
    # Cache the result
    _biomass_cache[cache_key][diameters_tuple] = result
    
    return result
"""
    
    # Insert the memoization code after the calculate_biomass_batch function
    def_pattern = r"def calculate_biomass_batch\([^)]*\):.*?return np\.array\(biomass_values\)"
    if re.search(def_pattern, content, re.DOTALL):
        content = re.sub(def_pattern, lambda m: m.group(0) + "\n\n" + memoize_code, content, flags=re.DOTALL)
    else:
        print("Warning: calculate_biomass_batch function not found")
    
    # 2. Replace calls to calculate_biomass_batch with cached version
    content = content.replace("biomass_values = calculate_biomass_batch(", 
                             "biomass_values = cached_calculate_biomass_batch(")
    content = content.replace("biomasss_values = calculate_biomass_batch(", 
                             "biomasss_values = cached_calculate_biomass_batch(")
    
    # 3. Optimize process_tree_column function to use vectorized operations for delta calculations
    process_tree_col_pattern = r"(# 计算后续年份的生物量增量\s+for k in range\(y_start \+ 1, y_end \+ 1\):.*?)return diameter"
    process_tree_col_replacement = """# 计算后续年份的生物量增量 - 使用向量化操作
    # 构建移位数据
    shifted_biomass = biomass.shift(1)
    shifted_biomasss = biomasss.shift(1)
    
    # 计算差值 - 向量化操作
    valid_mask = ~biomass.isna() & ~shifted_biomass.isna()
    delta_bio[valid_mask] = biomass[valid_mask] - shifted_biomass[valid_mask]
    
    valid_mask = ~biomasss.isna() & ~shifted_biomasss.isna()
    delta_bioo[valid_mask] = biomasss[valid_mask] - shifted_biomasss[valid_mask]
    
    return diameter"""
    
    try:
        content = re.sub(process_tree_col_pattern, process_tree_col_replacement, content, flags=re.DOTALL)
    except Exception as e:
        print(f"Error optimizing process_tree_column: {e}")
    
    # 4. Optimize DataFrame creation by using a single operation
    df_creation_pattern = r"(# 优化: 一次性创建DataFrame.*?dia_all = pd\.DataFrame\(data_columns\['dia'\]\).*?)bio_all = pd\.DataFrame"
    df_creation_replacement = """# 优化: 一次性创建DataFrame，避免频繁修改
    dataframes = {}
    for key in ['dia', 'bio', 'delta_dia', 'delta_bio', 'diaa', 'bioo', 'delta_diaa', 'delta_bioo', 'age']:
        dataframes[key] = pd.DataFrame(data_columns[key])
    
    dia_all = dataframes['dia']
    bio_all = pd.DataFrame"""
    
    try:
        content = re.sub(df_creation_pattern, df_creation_replacement, content, flags=re.DOTALL)
        
        # Add the rest of the DataFrame assignments
        content = content.replace("bio_all = pd.DataFrame(data_columns['bio'])", "bio_all = dataframes['bio']")
        content = content.replace("delta_dia_all = pd.DataFrame(data_columns['delta_dia'])", "delta_dia_all = dataframes['delta_dia']")
        content = content.replace("delta_bio_all = pd.DataFrame(data_columns['delta_bio'])", "delta_bio_all = dataframes['delta_bio']") 
        content = content.replace("diaa_all = pd.DataFrame(data_columns['diaa'])", "diaa_all = dataframes['diaa']")
        content = content.replace("bioo_all = pd.DataFrame(data_columns['bioo'])", "bioo_all = dataframes['bioo']")
        content = content.replace("delta_diaa_all = pd.DataFrame(data_columns['delta_diaa'])", "delta_diaa_all = dataframes['delta_diaa']")
        content = content.replace("delta_bioo_all = pd.DataFrame(data_columns['delta_bioo'])", "delta_bioo_all = dataframes['delta_bioo']")
        content = content.replace("age_all = pd.DataFrame(data_columns['age'])", "age_all = dataframes['age']")
    except Exception as e:
        print(f"Error optimizing DataFrame creation: {e}")
    
    # 5. Optimize file saving operations
    file_save_pattern = r"(file_saves = \[.*?for output_file, df in file_saves:.*?)df\.to_csv\(output_file, index=False\)"
    file_save_replacement = """file_saves = [
                (os.path.join(output_path, f"{file_prefix}_dia.csv"), dia_all),
                (os.path.join(output_path, f"{file_prefix}_bio.csv"), bio_all),
                (os.path.join(output_path, f"{file_prefix}_delta_dia.csv"), delta_dia_all),
                (os.path.join(output_path, f"{file_prefix}_delta_bio.csv"), delta_bio_all),
                (os.path.join(output_path, f"{file_prefix}_age.csv"), age_all),
            # 保存校正文件 - 包含校正代码
                (os.path.join(output_path, f"{file_prefix}_diaa_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), diaa_all),
                (os.path.join(output_path, f"{file_prefix}_bioo_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), bioo_all),
                (os.path.join(output_path, f"{file_prefix}_delta_diaa_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), delta_diaa_all),
                (os.path.join(output_path, f"{file_prefix}_delta_bioo_correction_{initial_width_code}_{geometric_code}_{bark_code}.csv"), delta_bioo_all)
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
                        logger.error(f"Error saving file: {e}")"""
    
    try:
        if "file_saves = [" in content:
            content = re.sub(file_save_pattern, file_save_replacement, content, flags=re.DOTALL)
    except Exception as e:
        print(f"Error optimizing file saving: {e}")
    
    # 6. Optimize metadata caching
    if "get_metadata_for_tree" in content:
        # Make sure metadata caching uses a better data structure
        content = content.replace("METADATA_CACHE = {}", "METADATA_CACHE = {} # Global cache for tree metadata")
    
    # 7. Reduce excessive logging
    # Replace logger.info with logger.debug for many routine operations
    content = content.replace('logger.info(f"Year {k} custom bark correction', 'logger.debug(f"Year {k} custom bark correction')
    content = content.replace('logger.info(f"Year {k} bark correction', 'logger.debug(f"Year {k} bark correction')
    content = content.replace('logger.info(f"Geometric correction', 'logger.debug(f"Geometric correction')
    content = content.replace('logger.info(f"Initial bark correction', 'logger.debug(f"Initial bark correction')
    content = content.replace('logger.info(f"Custom bark correction', 'logger.debug(f"Custom bark correction')
    
    # 8. Optimize the generate_random_values function
    rand_values_pattern = r"def generate_random_values\(min_value, max_value, times\):.*?return \[0\]"
    rand_values_replacement = """def generate_random_values(min_value, max_value, times):
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
    return list(random_values)[:times]"""
    
    try:
        content = re.sub(rand_values_pattern, rand_values_replacement, content, flags=re.DOTALL)
    except Exception as e:
        print(f"Error optimizing random values function: {e}")
    
    # Save the optimized file
    try:
        with open('plot_all_allometry.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully optimized plot_all_allometry.py")
    except Exception as e:
        print(f"Error saving optimized file: {e}")
        
if __name__ == "__main__":
    optimize_allometry() 