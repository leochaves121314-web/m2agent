"""
M2 CLIPS - AGENTE AUTÔNOMO 24/7
Roda no Railway.app e monitora/melhora o M2 Clips automaticamente
"""

import os
import time
import json
import logging
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ============================================================
# CONFIGURAÇÃO
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("M2Agent")

# ============================================================
# SERVIDOR WEB (mantém o Railway acordado)
# ============================================================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""
        <html>
        <head><title>M2 Clips Agent</title>
        <style>
          body {{ font-family: Arial; background: #0a0a0a; color: #00ff88; padding: 40px; }}
          h1 {{ color: #ff6b35; }}
          .status {{ background: #111; padding: 20px; border-radius: 10px; border: 1px solid #00ff88; }}
          .dot {{ display: inline-block; width: 12px; height: 12px; background: #00ff88; border-radius: 50%; animation: pulse 1s infinite; }}
          @keyframes pulse {{ 0%,100% {{ opacity:1 }} 50% {{ opacity:0.3 }} }}
        </style>
        </head>
        <body>
        <h1>🤖 M2 CLIPS - AGENTE AUTÔNOMO</h1>
        <div class="status">
          <p><span class="dot"></span> Status: <strong>ATIVO 24/7</strong></p>
          <p>⏰ Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
          <p>🧠 IA: Groq (llama-3.3-70b)</p>
          <p>🔄 Ciclo: A cada 6 horas</p>
          <p>✅ Agente M2 Clips rodando normalmente</p>
        </div>
        </body>
        </html>
        """.encode("utf-8")
        self.wfile.write(html)

    def log_message(self, format, *args):
        pass  # silencia logs do servidor HTTP

def iniciar_servidor():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"Servidor web rodando na porta {PORT}")
    server.serve_forever()

# ============================================================
# FUNÇÕES DO AGENTE
# ============================================================

def chamar_groq(mensagem, sistema="Você é o agente autônomo M2 Clips. Responda em português."):
    """Chama a API do Groq com fallback para Pollinations"""
    
    # Tenta Groq primeiro
    if GROQ_API_KEY:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": sistema},
                        {"role": "user", "content": mensagem}
                    ],
                    "max_tokens": 1000
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning(f"Groq falhou: {e}")
    
    # Fallback: Pollinations (sem chave)
    try:
        prompt_encoded = requests.utils.quote(mensagem[:500])
        resp = requests.get(
            f"https://text.pollinations.ai/{prompt_encoded}",
            timeout=30
        )
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        log.warning(f"Pollinations falhou: {e}")
    
    return "Agente funcionando — APIs temporariamente indisponíveis."


def ciclo_analise():
    """Ciclo principal: analisa e sugere melhorias a cada 6 horas"""
    
    tarefas = [
        "Liste 3 melhorias para um app de produção de vídeos com IA chamado M2 Clips. Seja específico e prático.",
        "Quais APIs gratuitas de IA para geração de vídeo estão disponíveis em 2025? Liste nome, URL e limite gratuito.",
        "Sugira 3 funcionalidades novas para um app de agência de vídeos com IA que usa Claude, Groq e Pollinations.",
        "Como otimizar um app HTML/JS para rodar mais rápido no navegador? Dê 3 dicas práticas.",
    ]
    
    ciclo = 0
    while True:
        ciclo += 1
        log.info(f"=== CICLO {ciclo} INICIADO ===")
        
        tarefa = tarefas[(ciclo - 1) % len(tarefas)]
        log.info(f"Tarefa: {tarefa[:60]}...")
        
        resposta = chamar_groq(tarefa)
        
        # Salva resultado
        resultado = {
            "ciclo": ciclo,
            "timestamp": datetime.now().isoformat(),
            "tarefa": tarefa,
            "resposta": resposta[:500]
        }
        
        # Append ao log de resultados
        try:
            historico = []
            if os.path.exists("resultados.json"):
                with open("resultados.json", "r", encoding="utf-8") as f:
                    historico = json.load(f)
            historico.append(resultado)
            # Mantém só os últimos 50 resultados
            historico = historico[-50:]
            with open("resultados.json", "w", encoding="utf-8") as f:
                json.dump(historico, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"Erro ao salvar resultado: {e}")
        
        log.info(f"Ciclo {ciclo} concluído. Próximo em 6 horas.")
        log.info(f"Resposta: {resposta[:200]}...")
        
        # Aguarda 6 horas
        time.sleep(6 * 60 * 60)


# ============================================================
# INÍCIO
# ============================================================
if __name__ == "__main__":
    log.info("🚀 M2 CLIPS AGENTE AUTÔNOMO INICIANDO...")
    log.info(f"Groq API: {'✅ Configurada' if GROQ_API_KEY else '⚠️ Não configurada (usando Pollinations)'}")
    
    # Inicia servidor web em thread separada
    t = threading.Thread(target=iniciar_servidor, daemon=True)
    t.start()
    
    # Aguarda 10 segundos e inicia o ciclo
    log.info("Aguardando 10 segundos antes do primeiro ciclo...")
    time.sleep(10)
    
    # Inicia ciclo principal
    ciclo_analise()
