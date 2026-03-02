"""
Configurações do Plugin
Responsabilidade: Gerenciar configurações e opções
"""
class SmearConfig:
    def __init__(self):
        # Configurações de física
        self.stiffness = 0.6
        self.trailing_stiffness = 0.4
        self.trailing_exponent = 2.0
        self.max_length = 50
        
        # Configurações de animação
        self.time_interval = 16  # ~60 FPS
        self.enabled = True
        
        # Configurações visuais
        self.smear_insert_mode = True
        self.smear_normal_mode = True
        
    def to_dict(self) -> dict:
        """Exporta configurações para dicionário"""
        return {
            'stiffness': self.stiffness,
            'trailing_stiffness': self.trailing_stiffness,
            'trailing_exponent': self.trailing_exponent,
            'max_length': self.max_length,
            'time_interval': self.time_interval,
            'enabled': self.enabled,
            'smear_insert_mode': self.smear_insert_mode,
            'smear_normal_mode': self.smear_normal_mode
        }
        
    def from_dict(self, config_dict: dict):
        """Importa configurações de dicionário"""
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)