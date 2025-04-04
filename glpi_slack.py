import requests
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

GLPI_URL = os.getenv("GLPI_URL")
GLPI_FRONT_URL = os.getenv("GLPI_FRONT_URL")
APP_TOKEN = os.getenv("APP_TOKEN")
USER_TOKEN = os.getenv("USER_TOKEN")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

HEADERS = {
    "App-Token": APP_TOKEN,
    "Authorization": f"user_token {USER_TOKEN}",
    "Content-Type": "application/json"
}

def iniciar_sessao():
    response = requests.get(f"{GLPI_URL}/initSession", headers=HEADERS)
    response.raise_for_status()
    token = response.json()["session_token"]
    print("✅ Sessão iniciada.")
    return token

def encerrar_sessao(token):
    headers = {**HEADERS, "Session-Token": token}
    requests.get(f"{GLPI_URL}/killSession", headers=headers)
    print("✅ Sessão encerrada.")

def get_ultimo_ticket(token):
    headers = {**HEADERS, "Session-Token": token}
    params = {
        "range": "0-0",
        "sort": "15",  # date_creation
        "order": "DESC"
    }
    response = requests.get(f"{GLPI_URL}/search/Ticket", headers=headers, params=params)
    response.raise_for_status()
    data = response.json().get("data", [])
    return data[0] if data else None

def get_nome_usuario(token, user_id):
    if not user_id:
        return "—"
    headers = {**HEADERS, "Session-Token": token}
    response = requests.get(f"{GLPI_URL}/User/{user_id}", headers=headers)
    if response.status_code == 200:
        usuario = response.json()
        nome = usuario.get("realname", "") + " " + usuario.get("firstname", "")
        return nome.strip() or usuario.get("name", f"ID {user_id}")
    return f"ID {user_id}"

def enviar_para_slack(ticket, criador_nome, tecnico_nome):
    tipos = {"1": "Incidente", "2": "Requisição"}
    prioridades = {"1": "Muito baixa", "2": "Baixa", "3": "Média", "4": "Alta", "5": "Muito alta"}
    status = {
        "1": "Novo", "2": "Atribuído", "3": "Planejado",
        "4": "Em andamento", "5": "Pendente", "6": "Resolvido", "7": "Fechado"
    }

    tipo = tipos.get(str(ticket.get("14")), "—")
    prioridade = prioridades.get(str(ticket.get("3")), "—")
    status_txt = status.get(str(ticket.get("12")), "—")
    ticket_id = ticket.get("2")
    link = f"{GLPI_FRONT_URL}/front/ticket.form.php?id={ticket_id}"

    payload = {
        "text": f":rotating_light: *NOVO CHAMADO NO GLPI*\n"
                f"> *ID:* {ticket_id}\n"
                f"> *Título:* {ticket.get('1')}\n"
                f"> *Entidade:* {ticket.get('80')}\n"
                f"> *Tipo:* {tipo}\n"
                f"> *Prioridade:* {prioridade}\n"
                f"> *Status:* {status_txt}\n"
                f"> *Criado por:* {criador_nome}\n"
                f"> *Técnico:* {tecnico_nome}\n"
                f"> *Data de abertura:* {ticket.get('15')}\n"
                f"> *Link:* <{link}>"
    }

    if SLACK_WEBHOOK_URL:
        requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    else:
        print("❌ Webhook do Slack não configurado.")

def logar_ticket(ticket, criador_nome, tecnico_nome):
    tipos = {"1": "Incidente", "2": "Requisição"}
    prioridades = {"1": "Muito baixa", "2": "Baixa", "3": "Média", "4": "Alta", "5": "Muito alta"}
    status = {
        "1": "Novo", "2": "Atribuído", "3": "Planejado",
        "4": "Em andamento", "5": "Pendente", "6": "Resolvido", "7": "Fechado"
    }

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    id_ticket = ticket.get("2")
    titulo = ticket.get("1")
    entidade = ticket.get("80")
    tipo = tipos.get(str(ticket.get("14")), "—")
    prioridade = prioridades.get(str(ticket.get("3")), "—")
    status_nome = status.get(str(ticket.get("12")), "—")
    data_abertura = ticket.get("15")
    link = f"{GLPI_FRONT_URL}/front/ticket.form.php?id={id_ticket}"

    log_line = (
        f"[{now}] ID: {id_ticket} | Título: {titulo} | Entidade: {entidade} | "
        f"Tipo: {tipo} | Prioridade: {prioridade} | Status: {status_nome} | "
        f"Criado por: {criador_nome} | Técnico: {tecnico_nome} | "
        f"Criado em: {data_abertura} | Link: {link}\n"
    )

    with open("glpi_tickets.log", "a", encoding="utf-8") as log_file:
        log_file.write(log_line)

def print_ticket(token, ticket):
    tipos = {"1": "Incidente", "2": "Requisição"}
    prioridades = {"1": "Muito baixa", "2": "Baixa", "3": "Média", "4": "Alta", "5": "Muito alta"}
    status = {
        "1": "Novo", "2": "Atribuído", "3": "Planejado",
        "4": "Em andamento", "5": "Pendente", "6": "Resolvido", "7": "Fechado"
    }

    id_ticket = ticket.get("2")
    titulo = ticket.get("1")
    entidade = ticket.get("80")
    tipo_id = str(ticket.get("14"))
    prioridade_id = str(ticket.get("3"))
    status_id = str(ticket.get("12"))
    tecnico_id = ticket.get("5")
    criador_id = ticket.get("4")
    data_criacao = ticket.get("15")
    link_chamado = f"{GLPI_FRONT_URL}/front/ticket.form.php?id={id_ticket}"

    tecnico_nome = get_nome_usuario(token, tecnico_id)
    criador_nome = get_nome_usuario(token, criador_id)

    print("\n📢 NOVO TICKET DETECTADO")
    print("─────────────────────────────")
    print(f"🆔 ID..........: {id_ticket}")
    print(f"📄 Título......: {titulo}")
    print(f"🏢 Entidade....: {entidade}")
    print(f"📂 Tipo........: {tipos.get(tipo_id, tipo_id)}")
    print(f"⚠️ Prioridade..: {prioridades.get(prioridade_id, prioridade_id)}")
    print(f"📶 Status......: {status.get(status_id, status_id)}")
    print(f"🧑‍💻 Técnico....: {tecnico_nome}")
    print(f"👤 Criado por..: {criador_nome}")
    print(f"🕒 Criado em...: {data_criacao}")
    print(f"🔗 Link........: {link_chamado}")
    print("─────────────────────────────")

    enviar_para_slack(ticket, criador_nome, tecnico_nome)
    logar_ticket(ticket, criador_nome, tecnico_nome)

def watcher():
    token = None
    try:
        token = iniciar_sessao()
        ultimo_id = None

        print("🔄 Monitorando chamados... (CTRL+C para sair)")

        while True:
            ticket = get_ultimo_ticket(token)
            if ticket:
                ticket_id = str(ticket.get("2"))
                status_id = str(ticket.get("12"))

                if ultimo_id is None:
                    ultimo_id = ticket_id  # primeira inicialização
                elif ticket_id != ultimo_id and status_id == "1":  # apenas status "Novo"
                    ultimo_id = ticket_id
                    print_ticket(token, ticket)

            print("⏱️  Chamados sendo monitorados...")
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n⛔ Monitoramento interrompido pelo usuário.")
    except Exception as e:
        print("❌ Erro:", e)
    finally:
        if token:
            encerrar_sessao(token)

if __name__ == "__main__":
    watcher()
