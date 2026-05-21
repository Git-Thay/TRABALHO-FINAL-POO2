import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

class NotificadorWhatsApp:
    def __init__(self):
        # NOTA: O token e o ID da Twilio ficam encapsulados aqui dentro.
        self.__account_sid = os.getenv("TWILIO_ACCOUNT_SID", "AC17bb0e00f44b1886c5137950f6363a4f")
        self.__auth_token = os.getenv("TWILIO_AUTH_TOKEN", "c4f66d60ce37a9d781cd15a0cb35a6c9")
        
        # O número padrão do Sandbox gratuito da Twilio
        self.__numero_remetente = "whatsapp:+14155238886"
        
        # Inicializa o cliente da API da Twilio
        self.__client = Client(self.__account_sid, self.__auth_token)

    def enviar_mensagem_validacao(self, nome_contato: str, telefone_destino: str) -> bool:
        """Envia a mensagem inicial pedindo para o contato responder SIM para validar o cadastro."""
        texto = (
            f"Olá {nome_contato}!\n\n"
            f"Você foi cadastrado no sistema Smart Guardian como responsável por uma criança.\n"
            f"Para sua segurança, responda esta mensagem apenas com a palavra *SIM* para ativar "
            f"o recebimento de alertas de emergência."
        )
        return self.__disparar_whatsapp(telefone_destino, texto)

    def enviar_alerta_emergencia(self, nome_contato: str, telefone_destino: str, nivel: int, minutos: int) -> bool:
        """Envia os alertas críticos conforme o tempo passa (2 min, 5 min, etc)."""
        if minutos == 2:
            texto = f"🚨 *AVISO IMPORTANTE (Nível {nivel})* 🚨\n\n{nome_contato}, o sistema detectou a criança sozinha no veículo há {minutos} minutos. Por favor, verifique imediatamente!"
        elif minutos == 5:
            texto = f"⚠️ *ALERTA URGENTE (Nível {nivel})* ⚠️\n\n{nome_contato}, ATENÇÃO! A criança continua sozinha no veículo há {minutos} minutos. Responda este alerta se estiver ciente!"
        else:
            texto = f"💥 *ALERTA CRÍTICO (Nível {nivel})* 💥\n\n{nome_contato}, a situação é grave! Criança sozinha há {minutos} minutos. Próximos níveis e autoridades estão sendo acionados."

        return self.__disparar_whatsapp(telefone_destino, texto)

    def __disparar_whatsapp(self, telefone_destino: str, texto: str) -> bool:
        """Método privado que faz a chamada real para a API da Twilio."""
        try:
            destino_formatado = f"whatsapp:{telefone_destino}"
            
            self.__client.messages.create(
                body=texto,
                from_=self.__numero_remetente,
                to=destino_formatado
            )
            print(f"[WhatsApp] Mensagem enviada com sucesso para {telefone_destino}")
            return True
            
        except TwilioRestException as e:
            print(f"[Erro Twilio] Falha ao enviar mensagem para {telefone_destino}: {e.msg}")
            return False