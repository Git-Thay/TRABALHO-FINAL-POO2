from enum import Enum
import uuid

class NivelAlerta(Enum):
    NIVEL_1 = 1  # Pais e convívio direto
    NIVEL_2 = 2  # Conhecidos/Tios (Secundários)
    NIVEL_3 = 3  # Autoridades (Bombeiros/Polícia)

class Contato:
    def __init__(self, nome: str, telefone: str, nivel: NivelAlerta):
        # Gerando ID automático oculto para o usuário (padrão UUID)
        self.__id = str(uuid.uuid4())
        
        # Atributos públicos e obrigatórios
        self.nome = nome
        self.telefone = self.__limpar_e_validar_telefone(telefone)
        self.nivel = nivel
        
        # Todo contato começa como não verificado (precisa responder SIM)
        self.verificado = False

    # Encapsulamento: Permitir ler o ID, mas não alterá-lo diretamente
    @property
    def id(self) -> str:
        return self.__id

    def verificar_contato(self):
        """Muda o status do contato para ativo após o fluxo do 'SIM'."""
        self.verificado = True

    def __limpar_e_validar_telefone(self, telefone: str) -> str:
        """Método privado para garantir que o telefone venha limpo e no formato correto."""
        numeros = "".join(c for c in telefone if c.isdigit())
        
        if not numeros.startswith("55"):
            numeros = "55" + numeros
            
        return f"+{numeros}"

    def obtener_dados_resumidos(self) -> dict:
        """Retorna um dicionário com os dados para exibição segura."""
        return {
            "nome": self.nome,
            "telefone": self.telefone,
            "nivel": self.nivel.name,
            "verificado": self.verificado
        }