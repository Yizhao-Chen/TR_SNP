#The function is to get the allometric relationships
#for each site
import csv
import math
import os
import logging
import pandas as pd

# 导入改进的allodb接口和树种映射表
try:
    from improved_allodb import estimate_biomass_using_get_biomass
    from species_mapper import SPECIES_CODE_MAP
    ALLODB_AVAILABLE = True
except ImportError:
    ALLODB_AVAILABLE = False
    logging.warning("improved_allodb模块未找到，将使用硬编码方程")

def allometric_dict(dbh, species_code, lat, lon, logger=None):
    """
    估算树木生物量 - 优先使用allodb包方程,回退到硬编码方程
    
    参数:
    dbh: 胸径(cm)
    species_code: 树种代码
    lat: 纬度
    lon: 经度
    logger: 日志记录器对象
    """
    biomass = 0
    
    #35.59,-94,usa,QUAL,380,1625,1993,ITRDB,ar059
    # 如果未找到树种代码,返回错误值  
    if not species_code:
        if logger:
            logger.warning(f"未找到树种代码")
        return -999
        
    # 尝试使用allodb估算生物量
    if ALLODB_AVAILABLE:
        try:
            latin_name = SPECIES_CODE_MAP.get(species_code)
            
            if latin_name:
                coords = None
                if lat is not None and lon is not None:
                    coords = (lon, lat)
                
                result = estimate_biomass_using_get_biomass(dbh, latin_name, coords=coords)
                if not result.empty and not pd.isna(result['agb'][0]):
                    if logger:
                        logger.info(f"使用allodb计算生物量成功: species_code={species_code}, latin_name={latin_name}, dbh={dbh}, biomass={result['agb'][0]}")
                    return result['agb'][0]
                else:
                    if logger:
                        logger.info(f"未找到匹配的生物量方程: species_code={species_code}, latin_name={latin_name}, dbh={dbh}, coords={coords}")
            else:
                if logger:
                    logger.warning(f"未找到对应的拉丁学名: species_code={species_code}")
                
        except Exception as e:
            if logger:
                logger.error(f"使用allodb估算生物量失败: {e}, species_code={species_code}, dbh={dbh}")
    
    # 如果allodb不可用或估算失败，回退到原有方法
    # 北美树种
    if (species_code == 'ABAM' or species_code == 'ABBA' or species_code == 'ABCO'
    or species_code == 'ABMA'):
        biomass = math.exp(-3.1774 + 2.6426 * math.log(dbh))

    if (species_code == 'ABLA'):
        biomass = math.exp(-2.3123  + 2.3482 * math.log(dbh))

    if (species_code == 'ACRU' or species_code == 'BELE'):
        biomass = math.exp(-1.9123 + 2.3651 * math.log(dbh))

    if (species_code == 'ACSH'):
        biomass = math.exp(-2.0127 + 2.4342 * math.log(dbh))

    if (species_code == 'CADE'):
        biomass = math.exp(-11.8235 + 2.7334 * math.log(dbh))

    if (species_code == 'CYGL' or species_code == 'CYOV'):
        biomass = math.exp(-1.326 + 2.761 * math.log(dbh))

    if (species_code == 'CHNO'or species_code == 'JUOC'):
        biomass = math.exp(-2.6327 + 2.4757 * math.log(dbh))

    if (species_code == 'FAGR'):
        biomass = 0.084 * math.pow(dbh,2.572)

    if (species_code == 'JUOS' or species_code == 'JUSC'):
        biomass = math.exp(-0.7152 + 1.7029 * math.log(dbh))

    if (species_code == 'JUVI'):
        biomass = math.exp(-2.0336 + 2.2592 * math.log(dbh))

    if (species_code == 'LALY' or species_code == 'LAOC'):
        biomass = math.exp(-2.3012 + 2.3853 * math.log(dbh))

    if (species_code == 'LITU'):
        biomass = math.exp(-2.48 + 2.4835 * math.log(dbh))

    if (species_code == 'PCEN'):
        biomass = math.exp(-3.03 + 2.5567 * math.log(dbh))

    if (species_code == 'PCGL'):
        biomass = math.exp(-2.1364 + 2.3233 * math.log(dbh))

    if (species_code == 'PCMA'):
        biomass = math.exp(-1.7823 + 2.1777 * math.log(dbh))

    if (species_code == 'PCPU'):
        biomass = math.exp(-2.1364 + 2.3233 * math.log(dbh))

    if (species_code == 'PCRU'):
        biomass = math.exp(-2.0773 + 2.3323 * math.log(dbh))

    if (species_code == 'PCSI'):
        biomass = math.exp(-3.03 + 2.5567 * math.log(dbh))

    if (species_code == 'PIAR' or species_code == 'PIBA' or species_code == 'PICO' or species_code == 'PIEC'
    or species_code == 'PIJE' or species_code == 'PILO' or species_code == 'PIMR' or species_code == 'PIPA'
    or species_code == 'PIPU'):
        biomass = math.exp(-3.0506 + 2.6465 * math.log(dbh))

    if (species_code == 'PIED' or species_code == 'PIRE' or species_code == 'PIRI' or species_code == 'PITA'):
        biomass = math.exp(-2.5356 + 2.4349 * math.log(dbh))

    if (species_code == 'PIFL' or species_code == 'PILA' or species_code == 'PIPO' or species_code == 'PIAL'
    or species_code == 'PISF'):
        biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))

    if (species_code == 'PIST'):
        biomass = math.exp(5.2831 + 2.0369 * math.log(dbh))

    if (species_code == 'PIVI'):
        biomass = math.exp(-2.5918 + 2.422 * math.log(dbh))

    if (species_code == 'PPDE' or species_code == 'PPGR'):
        biomass = math.exp(-2.2094 + 2.3867 * math.log(dbh))

    if (species_code == 'PPTR'):
        biomass = math.exp(4.4564 + 2.4486 * math.log(dbh))

    if (species_code == 'PSMA'):
        biomass = math.exp(-2.4623 + 2.4852 * math.log(dbh))

    if (species_code == 'PSME'):
        biomass = math.exp(-2.3298 + 2.4818 * math.log(dbh))

    if (species_code == 'QUAL' or species_code == 'QUCO'):
        biomass = math.exp(-2.0127 + 2.4342 * math.log(dbh))

    if (species_code == 'QUDG'):
        biomass = 0.0683*math.pow(dbh,2.5697)

    if (species_code == 'QUFA' or species_code == 'QULO' or species_code == 'QULY'):
        biomass = math.exp(-2.0127 + 2.4342 * math.log(dbh))

    if (species_code == 'QUMA' or species_code == 'QUMU' or species_code == 'QUPA'):
        biomass = 0.1447* math.pow(dbh,2.282)

    if (species_code == 'QURU' or species_code == 'QUSH' or species_code == 'QUST' or 'QUVE'):
        biomass = math.exp(-2.0127 + 2.4342 * math.log(dbh))

    if (species_code == 'TADI' or species_code =='THPL' or species_code == 'TSCR' or species_code == 'TSHE' or
    species_code == 'TSME' or species_code == 'LIDE'):
        biomass = math.exp(-2.7096 + 2.1942 * math.log(dbh))

    if (species_code == 'THOC'):
        biomass = math.exp(-2.0336 + 2.2592 * math.log(dbh))

    if (species_code == 'TSCA'):
        biomass = math.exp(-2.2304 + 2.4435 * math.log(dbh))

    if (species_code == 'CADN'):
        biomass = math.exp(-2.0705 + 2.441 * math.log(dbh))

    if (species_code == 'CDAT' or species_code == 'CDLI'):  # 大西洋雪松和黎巴嫩雪松使用相似方程
        biomass = math.exp(-2.5356 + 2.4349 * math.log(dbh))  # 使用针叶树的通用方程

    if (species_code == 'CHLA'):
        biomass = math.exp(-2.6327 + 2.4757 * math.log(dbh))

    if (species_code == 'MIXD'):
        biomass = math.exp(-2.5497 + 2.5011 * math.log(dbh))

    if (species_code == 'PINE'):
        biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))

    if (species_code == 'PISP'):
        biomass = math.exp(-3.2007 + 2.5339 * math.log(dbh))

    if (species_code == 'PITO'):
        biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))

    if (species_code == 'PLRA'):
        biomass = math.exp(-3.0506 + 2.6465 * math.log(dbh))

    if (species_code == 'QUCF' or species_code == 'QUSP'):
        biomass = math.exp(-2.0705 + 2.4410 * math.log(dbh))

    if (species_code == 'SAPC'):
        biomass = math.exp(-2.6863 + 2.4561 * math.log(dbh))
        
    if logger:
        logger.info(f"使用硬编码方程计算生物量: species_code={species_code}, dbh={dbh}, biomass={biomass}")
    
    return biomass
