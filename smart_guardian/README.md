# Smart Guardian

Sistema de segurança para monitoramento de crianças em veículos usando **YOLO** (visão computacional) e **WhatsApp via Twilio** para notificação em escada de alertas (2 / 5 / 8 minutos).

Projeto pensado como exercício de **POO 2**: encapsulamento (entidade `Contato`), Strategy (`CanalMensageria` → `WhatsAppTwilio` / `WhatsAppFake`), injeção de dependência (FastAPI `Depends`), repositório, e orquestração com `APScheduler`.

---

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- Twilio (WhatsApp Sandbox)
- APScheduler
- Ultralytics YOLO (v8/v10, arquivo `.pt`)
- OpenCV (somente para decodificar frames)

## Estrutura

```
app/
  api/rotas.py            # endpoints REST + webhook Twilio
  dominio/
    contato.py            # entidade + enums (NivelAlerta, StatusContato)
    repositorio.py        # repositório em memória (trocável)
    gerenciador.py        # estado de emergência + escada via APScheduler
  servicos/whatsapp.py    # Strategy: WhatsAppTwilio / WhatsAppFake
  ia/detector_yolo.py     # wrapper Ultralytics YOLO
  config.py               # Settings via pydantic-settings
  main.py                 # wiring (DI) + criar_app()
modelos/                  # coloque aqui seu best.pt
tests/                    # pytest
```

## Como rodar

```bash
criar pasta venv 
python -m venv .venv
ativar venv
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1

instalar pendencias
pip install -r requirements.txt
se der erro:
python.exe -m pip install --upgrade pip
pip install --upgrade setuptools wheel
e tentar novamente o requirements

se der erro de permição do windows fazer colar isto no power shell 
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

se nao estiver aceitando mesmo assim o requirements tentar isto para instalar manualmente:
pip install fastapi uvicorn ultralytics python-multipart opencv-python-headless pydantic


criar env com credenciais
TWILIO_ACCOUNT_SID=AC17bb0e00f44b1886c5137950f6363a4f
TWILIO_AUTH_TOKEN=5d890f29281102d1c328ecd1b7331c15
TWILIO_PHONE_FROM=whatsapp:+14155238886
TWILIO_PHONE_TO=whatsapp:+00000000000

cp .env.example .env        # preencha as credenciais Twilio
uvicorn app.main:app --reload
```
pode ser necessario instalar as seguintes bibliotecas
pip install fastapi uvicorn ultralytics python-multipart opencv-python-headless pydantic pydantic-settings python-dotenv apscheduler twilio requests pillow

Abra o Swagger em **http://localhost:8000/docs**.

> Se você **não** preencher as credenciais Twilio, o sistema sobe com um canal **fake** (apenas loga as mensagens). Útil para desenvolver sem custo.

## Configurando o Twilio Sandbox (passo a passo)

1. Crie conta em https://www.twilio.com/console.
2. Vá em **Messaging → Try it out → Send a WhatsApp message** (Sandbox).
3. No celular, envie a mensagem `join <duas-palavras>` para `+1 415 523 8886` (esse é o `TWILIO_WHATSAPP_FROM` padrão).
4. Copie `Account SID` e `Auth Token` para o `.env`.
5. Configure o **webhook de entrada** do Sandbox apontando para uma URL pública do seu servidor, por exemplo `https://<seu-ngrok>.ngrok.io/api/twilio/webhook` (método **POST**, content-type `application/x-www-form-urlencoded`).
6. Para testar localmente exponha sua porta com:
   ```bash
   ngrok http 8000
   ```

### Estabilizando o Sandbox

- Cada número precisa **refazer o `join <code>`** se ficar > 72h inativo — isso é limitação do Sandbox, não bug do código.
- Erros mais comuns que você vai ver nos logs:
  - `63007` – número não está no Sandbox (peça para o usuário enviar `join` de novo)
  - `63016` – fora da janela de 24h (em produção exige template aprovado)
  - `21610` – usuário deu opt-out (`stop`)

## Fluxo de uso

1. **Cadastrar contato** → `POST /api/contatos`
2. Usuário responde `SIM` no WhatsApp → Twilio chama `POST /api/twilio/webhook` → status vira `verificado`.
3. **IA detecta** criança sozinha:
   - chame `POST /api/deteccao/frame` enviando um JPG (precisa do `.pt` em `modelos/`), **ou**
   - use `POST /api/deteccao/simular?crianca_sozinha=true` para testar sem modelo.
4. O `GerenciadorAlertas` agenda 3 jobs no APScheduler (2/5/8 min). Cada nível envia para os contatos daquele nível **e dos inferiores**.
5. **Cancelar** após resgate: `POST /api/emergencia/cancelar` (remove todos os jobs).
6. `GET /api/emergencia/status` mostra o estado atual.

## Modelo YOLO

Coloque seu peso treinado em `modelos/best.pt` (ou ajuste `YOLO_MODEL_PATH`). O wrapper considera *criança sozinha* quando há ≥1 detecção de classe em `{crianca, child, kid, baby}` **e nenhuma** em `{adulto, adult, person_adult}`. Ajuste em `app/ia/detector_yolo.py` conforme o vocabulário do seu dataset.

## Testes

```bash
pytest -q
```

## Próximos passos sugeridos

- Trocar `RepositorioContatos` em memória por SQLAlchemy/SQLite sem alterar o domínio.
- Adicionar autenticação JWT nas rotas de cadastro.
- Persistir o estado de emergência (resistir a restart do processo).
- Em produção: migrar do Sandbox para um número WhatsApp Business aprovado.
