#!/usr/bin/env python
# -*- coding: utf-8 -*-
def estimate_biomass_using_get_biomass(dbh, taxa, coords=(-76.8, 39.2)):
    """
    使用allodb包的get_biomass函数估算树木生物量
    
    参数:
    dbh: 胸径值(cm)，可以是单个值或列表
    taxa: 树种分类信息，可以是属名或"属 种"格式
    coords: 坐标元组 (经度, 纬度)，默认为北美坐标(-76.8, 39.2)
    
    返回:
    pandas DataFrame: 包含生物量估算结果
    """
    import os
    import sys
    import tempfile
    import subprocess
    import pandas as pd
    import numpy as np
    
    # 创建临时文件
    temp_output = tempfile.NamedTemporaryFile(suffix='.csv', delete=False).name
    temp_script = tempfile.NamedTemporaryFile(suffix='.R', delete=False).name
    
    # 确保路径使用正斜杠，避免R中的转义问题
    temp_output_r = temp_output.replace('\\', '/')
    temp_script_r = temp_script.replace('\\', '/')
    
    try:
        # 解析属和种
        genus = taxa.split()[0] if " " in taxa else taxa
        species = taxa.split()[1] if " " in taxa else ""
        
        # 准备DBH数据
        if isinstance(dbh, (list, tuple)):
            dbh_str = f"c({','.join(map(str, dbh))})"
            is_list = True
        else:
            dbh_str = str(dbh)
            is_list = False
        
        # 准备坐标数据
        coords_str = f"c({coords[0]}, {coords[1]})"
        
        # 创建R脚本，增加错误检查和调试信息
        with open(temp_script, 'w') as f:
            f.write(f"""
            # 设置错误处理
            options(warn=1)  # 不将警告转换为错误
            
            # 加载包
            suppressPackageStartupMessages(library(allodb))
            
            # 检查输入参数的有效性
            check_taxa <- function(genus, species) {{
                # 获取allodb中所有可用的属和种
                data("equations", package="allodb")
                available_taxa <- unique(equations$equation_taxa)
                
                # 构建完整的分类名
                full_name <- if(species == "") genus else paste(genus, species)
                
                # 检查是否存在匹配的方程
                matches <- grep(paste0("^", genus), available_taxa, value=TRUE)
                if (length(matches) == 0) {{
                    stop(paste("No equations found for genus", genus))
                }}
                
                if (species != "") {{
                    species_matches <- grep(paste0("^", full_name, "$"), available_taxa, value=TRUE)
                    if (length(species_matches) == 0) {{
                        warning(paste("No exact match for species", full_name, "- falling back to genus level equations"))
                    }}
                }}
                
                # 打印可用的方程
                # cat("Available equations for taxa:\\n")
                # print(matches)
            }}
            
            tryCatch({{
                # 检查属种是否存在于数据库中
                check_taxa("{genus}", "{species}")
                
                # 使用get_biomass函数
                result <- get_biomass(
                    dbh = {dbh_str},
                    genus = "{genus}",
                    species = "{species}",
                    coords = {coords_str}
                )
                
                # 打印结果的详细信息
                cat("\\nBiomass calculation results:\\n")
                print(result)
                
                # 创建输出数据框
                dbh_values <- {dbh_str}
                if(is.numeric(result)) {{
                    output <- data.frame(dbh = dbh_values, agb = result)
                }} else {{
                    output <- result
                }}
                
                # 保存结果
                write.csv(output, "{temp_output_r}", row.names=FALSE)
                cat("SUCCESS\\n")
            }}, error=function(e) {{
                cat("ERROR:", conditionMessage(e), "\\n")
                
                # 创建空结果数据框
                dbh_values <- {dbh_str}
                output <- data.frame(dbh = dbh_values, agb = NA)
                write.csv(output, "{temp_output_r}", row.names=FALSE)
            }})
            """)
        
        # 执行R脚本
        result = subprocess.run(
            ["Rscript", temp_script], 
            capture_output=True, 
            text=True
        )
        
        # 只在出错时打印R脚本的输出
        if "ERROR:" in result.stdout or result.stderr:
            print("R script errors:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
        
        # 检查输出中是否有错误信息
        if "ERROR:" in result.stdout:
            print(f"R脚本执行出错: {result.stdout}")
            return pd.DataFrame({'dbh': dbh if is_list else [dbh], 'agb': [np.nan] * (len(dbh) if is_list else 1)})
            
        if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            biomass_df = pd.read_csv(temp_output)
            return biomass_df
        else:
            return pd.DataFrame({'dbh': dbh if is_list else [dbh], 'agb': [np.nan] * (len(dbh) if is_list else 1)})
    
    except Exception as e:
        print(f"执行R脚本时出错: {e}")
        return pd.DataFrame({'dbh': dbh if is_list else [dbh], 'agb': [np.nan] * (len(dbh) if is_list else 1)})
    
    finally:
        # 清理临时文件
        try:
            os.remove(temp_script)
            if os.path.exists(temp_output):
                os.remove(temp_output)
        except:
            pass

# 添加批量处理函数，大幅减少R脚本调用次数
def batch_estimate_biomass(dbh_list, taxa, coords=(-76.8, 39.2)):
    """
    批量估算树木生物量，大幅提高性能
    
    参数:
    dbh_list: 胸径列表，每个元素可以是单个值或列表
    taxa: 树种分类信息，可以是属名或"属 种"格式
    coords: 坐标元组 (经度, 纬度)，默认为北美坐标(-76.8, 39.2)
    
    返回:
    pandas DataFrame: 包含所有生物量估算结果
    """
    import os
    import sys
    import tempfile
    import subprocess
    import pandas as pd
    import numpy as np
    import json
    
    # 创建临时文件
    temp_output = tempfile.NamedTemporaryFile(suffix='.csv', delete=False).name
    temp_script = tempfile.NamedTemporaryFile(suffix='.R', delete=False).name
    
    # 确保路径使用正斜杠，避免R中的转义问题
    temp_output_r = temp_output.replace('\\', '/')
    temp_script_r = temp_script.replace('\\', '/')
    
    try:
        # 解析属和种
        genus = taxa.split()[0] if " " in taxa else taxa
        species = taxa.split()[1] if " " in taxa else ""
        
        # 准备坐标数据
        coords_str = f"c({coords[0]}, {coords[1]})"
        
        # 将所有DBH值扁平化为一个大列表
        all_dbh = []
        id_mapping = []  # 记录每个DBH值的原始位置
        
        for i, dbh in enumerate(dbh_list):
            try:
                if isinstance(dbh, (list, tuple, np.ndarray)):
                    # 处理数组/列表
                    for j, val in enumerate(dbh):
                        try:
                            # 处理NaN和None值
                            if val is None or (isinstance(val, float) and np.isnan(val)):
                                all_dbh.append(0.01)  # 使用小值代替NaN
                            else:
                                all_dbh.append(float(val))
                            id_mapping.append((i, j))
                        except (ValueError, TypeError):
                            print(f"警告: 无法转换值 {val} 为浮点数，使用默认值0.01")
                            all_dbh.append(0.01)
                            id_mapping.append((i, j))
                else:
                    # 处理单个值
                    if dbh is None or (isinstance(dbh, float) and np.isnan(dbh)):
                        all_dbh.append(0.01)
                    else:
                        all_dbh.append(float(dbh))
                    id_mapping.append((i, 0))
            except Exception as e:
                print(f"处理DBH值时出错: {e}，使用默认值0.01")
                if isinstance(dbh, (list, tuple, np.ndarray)):
                    for j in range(len(dbh)):
                        all_dbh.append(0.01)
                        id_mapping.append((i, j))
                else:
                    all_dbh.append(0.01)
                    id_mapping.append((i, 0))
        
        # 将DBH列表转换为R格式 - 确保没有方括号，直接用逗号分隔数字
        if len(all_dbh) == 0:
            print("警告: 没有有效的DBH值，使用默认值0.01")
            all_dbh = [0.01]
            
        dbh_str = ','.join(str(x) for x in all_dbh)
        
        # 创建R脚本
        with open(temp_script, 'w') as f:
            f.write(f"""
            # 设置错误处理
            options(warn=1)
            
            # 加载包
            suppressPackageStartupMessages(library(allodb))
            
            # 批量处理函数
            process_batch <- function() {{
                # 获取allodb中所有可用的属和种
                data("equations", package="allodb")
                
                # 使用get_biomass函数进行批量计算
                result <- get_biomass(
                    dbh = c({dbh_str}),
                    genus = "{genus}",
                    species = "{species}",
                    coords = {coords_str}
                )
                
                # 创建输出数据框
                output <- data.frame(dbh = c({dbh_str}), agb = result)
                
                # 保存结果
                write.csv(output, "{temp_output_r}", row.names=FALSE)
                cat("SUCCESS\\n")
            }}
            
            # 执行批处理
            tryCatch({{
                process_batch()
            }}, error=function(e) {{
                cat("ERROR:", conditionMessage(e), "\\n")
                
                # 创建空结果数据框
                output <- data.frame(dbh = c({dbh_str}), agb = rep(NA, length(c({dbh_str}))))
                write.csv(output, "{temp_output_r}", row.names=FALSE)
            }})
            """)
        
        # 执行R脚本
        result = subprocess.run(
            ["Rscript", temp_script], 
            capture_output=True, 
            text=True
        )
        
        # 只在出错时打印R脚本的输出
        if "ERROR:" in result.stdout or result.stderr:
            print("R script errors:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
        
        # 检查输出
        if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            try:
                # 读取所有结果
                all_results = pd.read_csv(temp_output)
                
                # 根据原始位置重组结果
                results = []
                for i, _ in enumerate(dbh_list):
                    if isinstance(dbh_list[i], (list, tuple)):
                        # 找出所有对应于这个列表的结果
                        indices = [j for j, (idx, _) in enumerate(id_mapping) if idx == i]
                        if indices and len(indices) > 0:
                            subset_results = all_results.iloc[indices]
                            # 确保结果长度与输入长度匹配
                            if len(subset_results) != len(dbh_list[i]):
                                print(f"警告: 结果长度与输入长度不匹配, 预期: {len(dbh_list[i])}, 实际: {len(subset_results)}")
                                # 如果长度不匹配，使用NaN填充缺失值
                                temp_df = pd.DataFrame({'dbh': dbh_list[i], 'agb': [np.nan] * len(dbh_list[i])})
                                for j, idx in enumerate(indices):
                                    if j < len(temp_df):
                                        temp_df.iloc[j, 1] = subset_results.iloc[min(j, len(subset_results)-1)]['agb']
                                results.append(temp_df)
                            else:
                                results.append(subset_results)
                        else:
                            # 创建空结果
                            results.append(pd.DataFrame({'dbh': dbh_list[i], 'agb': [np.nan] * len(dbh_list[i])}))
                    else:
                        # 找出对应于这个单值的结果
                        indices = [j for j, (idx, _) in enumerate(id_mapping) if idx == i]
                        if indices and len(indices) > 0:
                            results.append(all_results.iloc[indices])
                        else:
                            # 创建空结果
                            results.append(pd.DataFrame({'dbh': [dbh_list[i]], 'agb': [np.nan]}))
                
                return results
            except Exception as e:
                print(f"处理批量结果时出错: {e}")
                # 回退到创建空结果
                return [pd.DataFrame({'dbh': dbh if isinstance(dbh, (list, tuple)) else [dbh], 
                                    'agb': [np.nan] * (len(dbh) if isinstance(dbh, (list, tuple)) else 1)}) 
                       for dbh in dbh_list]
        else:
            # 创建空结果
            return [pd.DataFrame({'dbh': dbh if isinstance(dbh, (list, tuple)) else [dbh], 
                                'agb': [np.nan] * (len(dbh) if isinstance(dbh, (list, tuple)) else 1)}) 
                   for dbh in dbh_list]
    
    except Exception as e:
        print(f"批量执行R脚本时出错: {e}")
        return [pd.DataFrame({'dbh': dbh if isinstance(dbh, (list, tuple)) else [dbh], 
                             'agb': [np.nan] * (len(dbh) if isinstance(dbh, (list, tuple)) else 1)}) 
               for dbh in dbh_list]
    
    finally:
        # 清理临时文件
        try:
            os.remove(temp_script)
            if os.path.exists(temp_output):
                os.remove(temp_output)
        except:
            pass

# 增加一个缓存装饰器以避免对相同参数的重复计算
def memoize(func):
    """缓存函数结果的装饰器"""
    cache = {}
    
    def wrapper(*args, **kwargs):
        # 创建一个键来唯一标识函数调用
        key = str(args) + str(sorted(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    
    return wrapper

# 应用缓存装饰器
estimate_biomass_using_get_biomass_cached = memoize(estimate_biomass_using_get_biomass)

def test_get_biomass_function():
    """测试使用get_biomass的生物量估算函数"""
    #from estimate_biomass_using_get_biomass import estimate_biomass_using_get_biomass
    
    print("===== 测试 get_biomass 功能 =====")
    
    try:
        # 测试单个值
        print("\n1. 单个DBH值测试:")
        dbh_value = 30
        result = estimate_biomass_using_get_biomass(dbh_value, "Quercus")
        print(f"橡树(Quercus)生物量: {result.iloc[0]['agb']} kg")
        
        # 测试多个值
        print("\n2. 多个DBH值测试:")
        dbh_values = [10, 20, 30, 40, 50]
        result = estimate_biomass_using_get_biomass(dbh_values, "Pinus")
        print("松树(Pinus)生物量:")
        print(result)
        
        # 测试使用属和种
        print("\n3. 使用属和种测试:")
        result = estimate_biomass_using_get_biomass(30, "Quercus rubra")
        print(f"红橡树(Quercus rubra)生物量: {result.iloc[0]['agb']} kg")
        
        # 测试使用坐标
        print("\n4. 使用坐标测试:")
        result = estimate_biomass_using_get_biomass(30, "Acer", coords=(-76.8, 39.2))
        print(f"枫树(Acer)在坐标(-76.8, 39.2)处的生物量: {result.iloc[0]['agb']} kg")
        
        # 测试不同区域的树种
        print("\n5. 跨区域树种测试:")
        species_list = ["Pinus", "Quercus", "Acer", "Fagus", "Tsuga"]
        for sp in species_list:
            result = estimate_biomass_using_get_biomass(25, sp)
            print(f"{sp}生物量: {result.iloc[0]['agb']} kg")
            
        # 与硬编码方程对比
        print("\n6. 与硬编码方程对比:")
        dbh_test = 35
        import math
        hardcoded_biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh_test))  # PIPO方程
        allodb_biomass = estimate_biomass_using_get_biomass(dbh_test, "Pinus ponderosa").iloc[0]['agb']
        print(f"PIPO硬编码方程生物量: {hardcoded_biomass:.2f} kg")
        print(f"allodb生物量: {allodb_biomass:.2f} kg")
        
        # 测试批处理功能
        print("\n7. 批处理功能测试:")
        dbh_batch = [25, [10, 20, 30], 40]
        results = batch_estimate_biomass(dbh_batch, "Quercus")
        for i, res in enumerate(results):
            print(f"批次 {i+1} 结果:")
            print(res)
        
        return True
    
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_get_biomass_function()
    print("\n===== 测试结果 =====")
    print("get_biomass功能测试:" + ("成功" if success else "失败"))