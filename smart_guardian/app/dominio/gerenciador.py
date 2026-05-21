import time
from typing import List
from app.dominio.contato import Contato, NivelAlerta
from app.servicos.whatsapp import NotificadorWhatsApp

class GerenciadorAlerta:
    def __init__(self, notificador: NotificadorWhatsApp):
        self.__contatos: List[Contato] = []
        self.__notificador = notificador
        
        # Atributos de controle do cronômetro de emergência focado na criança
        self.__crianca_sozinha = False
        self.__tempo_inicio = None
        self.__minutos_alertados = set()

    def adicionar_contato(self, contato: Contato):
        """Cadastra um novo contato no sistema."""
        self.__contatos.append(contato)
        self.__notificador.enviar_mensagem_validacao(contato.nome, contato.telefone)
        print(f"[Gerenciador] Contato {contato.nome} adicionado e mensagem de validação enviada.")

    def obtener_contatos(self) -> List[Contato]:
        """Retorna todos os contatos cadastrados."""
        return self.__contatos

    def atualizar_status_verificacao(self, telefone: str) -> bool:
        """Procura o contato pelo telefone e ativa o cadastro (quando responder SIM)."""
        for contato in self.__contatos:
            if contato.telefone == telefone:
                contato.verificar_contato()
                print(f"[Gerenciador] Status do contato {contato.nome} atualizado para VERIFICADO.")
                return True
        return False

    def processar_deteccao(self, detectou_crianca_sozinha: bool):
        """
        Recebe o sinal da Visão Computacional.
        Controla o cronômetro e decide quem alertar baseando-se nos minutos decorridos.
        """
        # Caso 1: A criança foi detectada sozinha AGORA (Início da emergência)
        if detectou_crianca_sozinha and not self.__crianca_sozinha:
            self.__crianca_sozinha = True
            self.__tempo_inicio = time.time()
            self.__minutos_alertados.clear()
            print("\n🚨 [EMERGÊNCIA] Criança detectada sozinha! Cronômetro iniciado.")
            return

        # Caso 2: O carro está limpo ou os pais voltaram (Fim da emergência)
        if not detectou_crianca_sozinha and self.__crianca_sozinha:
            self.__crianca_sozinha = False
            self.__tempo_inicio = None
            self.__minutos_alertados.clear()
            print("\n✅ [SISTEMA] Situação normalizada ou responsável presente. Cronômetro zerado.")
            return

        # Caso 3: A emergência continua rodando, calcula o tempo decorrido
        if self.__crianca_sozinha:
            tempo_decorrido_segundos = time.time() - self.__tempo_inicio
            minutos_decorridos = int(tempo_decorrido_segundos) # 1 segundo = 1 minuto simulado para testes

            if minutos_decorridos in self.__minutos_alertados:
                return

            if minutos_decorridos == 2:
                self.__disparar_alertas_por_nivel([NivelAlerta.NIVEL_1], minutos_decorridos)
                self.__minutos_alertados.add(minutos_decorridos)
                
            elif minutos_decorridos == 5:
                self.__disparar_alertas_por_nivel([NivelAlerta.NIVEL_1], minutos_decorridos)
                self.__minutos_alertados.add(minutos_decorridos)
                
            elif minutos_decorridos == 8:
                self.__disparar_alertas_por_nivel([NivelAlerta.NIVEL_1, NivelAlerta.NIVEL_2], minutos_decorridos)
                self.__minutos_alertados.add(minutos_decorridos)
                
            elif minutos_decorridos == 10:
                self.__disparar_alertas_por_nivel([NivelAlerta.NIVEL_1, NivelAlerta.NIVEL_2], minutos_decorridos)
                self.__minutos_alertados.add(minutos_decorridos)
                
            elif minutos_decorridos >= 30 and (minutos_decorridos % 5 == 0): 
                self.__disparar_alertas_por_nivel([NivelAlerta.NIVEL_1, NivelAlerta.NIVEL_2, NivelAlerta.NIVEL_3], minutos_decorridos)
                self.__minutos_alertados.add(minutos_decorridos)

    def __disparar_alertas_por_nivel(self, niveis_alvo: List[NivelAlerta], minutos: int):
        """Método privado que filtra os contatos verificados pelos níveis alvos e dispara as mensagens."""
        print(f"\n[ALERTA COLETIVO] Disparando notificações de {minutos} minutos...")
        
        for contato in self.__contatos:
            if contato.nivel in niveis_alvo:
                if contato.nivel == NivelAlerta.NIVEL_3 or contato.verificado:
                    self.__notificador.enviar_alerta_emergencia(
                        nome_contato=contato.nome,
                        telefone_destino=contato.telefone,
                        nivel=contato.nivel.value,
                        minutos=minutos
                    )
                else:
                    print(f"[Aviso] Contato {contato.nome} (Nível {contato.nivel.name}) está na lista de envio, mas não confirmou o cadastro com 'SIM'. Alerta ignorado para ele.")