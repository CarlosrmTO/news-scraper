"""
Competitor configurations package.

This package contains configurations for various news websites that are considered
competitors. Each competitor has its own configuration file in the config directory.
"""

from .config.el_mundo import get_config as get_el_mundo_config
from .config.el_confidencial import get_config as get_el_confidencial_config
from .config.infobae import get_config as get_infobae_config
from .config.libertad_digital import get_config as get_libertad_digital_config
from .config.voz_populi import get_config as get_voz_populi_config
from .config.publico import get_config as get_publico_config
from .config.okdiario import get_config as get_okdiario_config
from .config.el_pais import get_config as get_el_pais_config
from .config.eldiario import get_config as get_eldiario_config
from .config.la_razon import get_config as get_la_razon_config
from .config.abc import get_config as get_abc_config
from .config.el_espanol import get_config as get_el_espanol_config
from .config.el_periodico import get_config as get_el_periodico_config
from .config.veinte_minutos import get_config as get_20minutos_config

def get_all_competitors():
    """
    Get configurations for all competitors.
    
    Returns:
        list: List of configuration dictionaries for all competitors
    """
    return [
        get_el_mundo_config(),
        get_el_confidencial_config(),
        get_infobae_config(),
        get_libertad_digital_config(),
        get_voz_populi_config(),
        get_publico_config(),
        get_okdiario_config(),
        get_el_pais_config(),
        get_eldiario_config(),
        get_la_razon_config(),
        get_abc_config(),
        get_el_espanol_config(),
        get_el_periodico_config(),
        get_20minutos_config()
    ]

def get_competitor_by_name(name):
    """
    Get configuration for a specific competitor by name.
    
    Args:
        name (str): Name of the competitor to retrieve
        
    Returns:
        dict: Configuration for the requested competitor, or None if not found
    """
    for competitor in get_all_competitors():
        if competitor['name'].lower() == name.lower():
            return competitor
    return None
