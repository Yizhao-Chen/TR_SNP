import re
import os

def apply_performance_fixes():
    # Read the current file
    with open('plot_all_allometry_species.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Make backup
    with open('plot_all_allometry_species.py.performance_backup', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 1. Reduce excessive logging
    # Replace logger.info with logger.debug for many routine operations
    content = content.replace('logger.info(f"Year {k} custom bark correction', 'logger.debug(f"Year {k} custom bark correction')
    content = content.replace('logger.info(f"Year {k} bark correction', 'logger.debug(f"Year {k} bark correction')
    content = content.replace('logger.info(f"Geometric correction', 'logger.debug(f"Geometric correction')
    content = content.replace('logger.info(f"Initial bark correction', 'logger.debug(f"Initial bark correction')
    content = content.replace('logger.info(f"Custom bark correction', 'logger.debug(f"Custom bark correction')
    
    # 2. Add memoization for bark_dict_species and calculate_biomass_batch functions
    memoization_code = """
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
"""
    
    # Insert memoization code after the imports
    import_section_end = content.find("# Import bark thickness calculation function")
    content = content[:import_section_end] + memoization_code + content[import_section_end:]
    
    # 3. Replace calls to calculate_biomass_batch with cached version
    content = content.replace("biomass_values = calculate_biomass_batch(", 
                            "biomass_values = cached_calculate_biomass_batch(")
    content = content.replace("biomasss_values = calculate_biomass_batch(", 
                            "biomasss_values = cached_calculate_biomass_batch(")
    
    # 4. Optimize data frame creation to use fewer operations
    # Find the part where we create all the DataFrames at once
    df_creation_pattern = r"# 完成数据收集后，一次性创建DataFrame.*?final_age = pd\.DataFrame\(data_columns\['age'\]\)"
    df_creation_replacement = """# 完成数据收集后，一次性创建DataFrame，避免频繁插入列导致的碎片化
        dataframes = {}
        for key in ['dia', 'bio', 'delta_dia', 'delta_bio', 'diaa', 'bioo', 'delta_diaa', 'delta_bioo', 'age']:
            dataframes[key] = pd.DataFrame(data_columns[key])
        
        final_dia = dataframes['dia']
        final_bio = dataframes['bio']
        final_delta_dia = dataframes['delta_dia']
        final_delta_bio = dataframes['delta_bio']
        final_diaa = dataframes['diaa']
        final_bioo = dataframes['bioo']
        final_delta_diaa = dataframes['delta_diaa']
        final_delta_bioo = dataframes['delta_bioo']
        final_age = dataframes['age']"""
    
    content = re.sub(df_creation_pattern, df_creation_replacement, content, flags=re.DOTALL)
    
    # 5. Optimize the loop for calculating biomass delta
    # We'll modify this to use vectorized operations
    biomass_delta_pattern = r"# 计算后续年份的生物量增量\s+for k in range\(y_start \+ 1, y_end \+ 1\):.*?delta_bioo\[k\] = biomasss\[k\] - biomasss\[k-1\]"
    biomass_delta_replacement = """# 计算后续年份的生物量增量 - 使用向量化操作
                # 构建移位数据
                shifted_biomass = biomass.shift(1)
                shifted_biomasss = biomasss.shift(1)
                
                # 计算差值
                valid_mask = ~biomass.isna() & ~shifted_biomass.isna()
                delta_bio[valid_mask] = biomass[valid_mask] - shifted_biomass[valid_mask]
                
                valid_mask = ~biomasss.isna() & ~shifted_biomasss.isna()
                delta_bioo[valid_mask] = biomasss[valid_mask] - shifted_biomasss[valid_mask]"""
    
    content = re.sub(biomass_delta_pattern, biomass_delta_replacement, content, flags=re.DOTALL)
    
    # Write the optimized file
    with open('plot_all_allometry_species.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Performance optimizations applied!")

if __name__ == "__main__":
    apply_performance_fixes() 