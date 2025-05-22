#The function is to get the bark width estimations from existing publications

import csv
import math
import os

def bark_dict_species(region, species, dbh):
    """
    Calculate bark thickness based on species and dbh
    
    Parameters:
    region: region identifier (not used in most formulas but kept for compatibility)
    species: species code (e.g., 'BEPE', 'PISY')
    dbh: diameter at breast height in cm
    
    Returns:
    bark_thickness: single-side bark thickness in cm
    """
    
    # Species code to formula mapping
    if species == "BEPE":  # Betula pendula (European white birch)
        # Formula: BT = (dbh * (1 - math.sqrt(1 - 25.502 * dbh**(-0.289) / 100)))/2
        bark_thickness = (dbh * (1 - math.sqrt(1 - 25.502 * dbh**(-0.289) / 100)))/2
    
    elif species == "FASY":  # Fagus sylvatica (European beech)
        # Formula: BT = (0.01149*DBH^0.8516)/100
        bark_thickness = (0.01149 * dbh**0.8516) / 100
    
    elif species == "PCAB":  # Picea abies (Norway spruce)
        # Formula: BT = (0.02408*DBH^0.8723)/100
        bark_thickness = (0.02408 * dbh**0.8723) / 100
    
    elif species == "PIPN":  # Pinus pinaster (Maritime pine)
        # Formula: BT = 0.103*DBH^1.023
        bark_thickness = 0.103 * dbh**1.023
    
    elif species == "PISY":  # Pinus sylvestris (Scots pine)
        # Formula: BT = (dbh * (1 - math.sqrt(1 - 75.492 * dbh**(-0.654) / 100)))/2
        bark_thickness = (dbh * (1 - math.sqrt(1 - 75.492 * dbh**(-0.654) / 100)))/2
    
    elif species == "PONI":  # Populus nigra (Black poplar)
        # Formula: BT = 0.081*DBH
        bark_thickness = 0.081 * dbh
    
    elif species == "QUPE":  # Quercus petraea (Sessile Oak)
        # Formula: BT = (0.02748*DBH^0.6759)/100
        bark_thickness = (0.02748 * dbh**0.6759) / 100
    
    else:
        # Default thickness for unknown species (5% of dbh)
        bark_thickness = 0.05 * dbh
    
    return bark_thickness
