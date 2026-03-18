# -*- coding: utf-8 -*-
"""Language Manager for h3sed.

Provides dynamic language switching between English and Chinese.
"""

_current_language = "en"

def get_current_language():
    """Return the current language code ('en' or 'zh')."""
    return _current_language

def set_language(lang):
    """Set the current language and apply translations.
    
    Args:
        lang: Language code - 'en' for English, 'zh' for Chinese
        
    Returns:
        True if language was set successfully, False otherwise
    """
    global _current_language
    
    if lang not in ("en", "zh"):
        return False
    
    _current_language = lang
    
    if lang == "zh":
        try:
            import h3sed.metadata_zh as metadata_zh
            metadata_zh.set_chinese()
            return True
        except Exception:
            return False
    else:
        _current_language = "en"
        return True

def reload_original_metadata():
    """Reload original English metadata."""
    global _current_language
    _current_language = "en"

def is_chinese():
    """Return True if current language is Chinese."""
    return _current_language == "zh"
