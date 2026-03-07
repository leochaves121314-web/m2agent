"""
M2 SUPREME AGENT v3.0
Agente autonomo 24/7 com painel de controle completo
"""

import os
import time
import json
import logging
import requests
import threading
import subprocess
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================================
# CONFIGURACAO
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("M2Supreme")

# Estado global do agente
estado = {
    "ciclos": 0,
    "apis_ativas": {},
    "historico": [],
    "status": "Iniciando...",
    "ultima_acao": "",
    "inicio": datetime.now().isoformat()
}

# ============================================================
# SISTEMA DE APIs COM FALLBACK
# ============================================================

def chamar_ia(mensagem, sistema="Voce e o M2 Supreme Agent. Responda em portugues. Seja direto e pratico."):
    """Tenta todas as IAs na ordem ate uma funcionar"""

    # 1. Groq
    if GROQ_API_KEY:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": [
                    {"role": "system", "content": sistema},
                    {"role": "user", "content": mensagem}
                ], "max_tokens": 2000},
                timeout=30
            )
            if r.status_code == 200:
                registrar_api_ativa("Groq", "texto")
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning(f"Groq falhou: {e}")

    # 2. Together AI
    together_key = os.environ.get("TOGETHER_API_KEY", "")
    if together_key:
        try:
            r = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={"Authorization": f"Bearer {together_key}", "Content-Type": "application/json"},
                json={"model": "meta-llama/Llama-3-70b-chat-hf", "messages": [
                    {"role": "user", "content": mensagem}
                ], "max_tokens": 2000},
                timeout=30
            )
            if r.status_code == 200:
                registrar_api_ativa("Together AI", "texto")
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning(f"Together falhou: {e}")

    # 3. Mistral
    mistral_key = os.environ.get("MISTRAL_API_KEY", "")
    if mistral_key:
        try:
            r = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"},
                json={"model": "mistral-small-latest", "messages": [
                    {"role": "user", "content": mensagem}
                ], "max_tokens": 2000},
                timeout=30
            )
            if r.status_code == 200:
                registrar_api_ativa("Mistral AI", "texto")
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning(f"Mistral falhou: {e}")

    # 4. OpenRouter (modelos gratuitos)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    if openrouter_key:
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
                json={"model": "mistralai/mistral-7b-instruct:free", "messages": [
                    {"role": "user", "content": mensagem}
                ]},
                timeout=30
            )
            if r.status_code == 200:
                registrar_api_ativa("OpenRouter", "texto")
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning(f"OpenRouter falhou: {e}")

    # 5. Pollinations (sem chave, sempre disponivel)
    try:
        prompt_enc = urllib.parse.quote(mensagem[:800])
        r = requests.get(f"https://text.pollinations.ai/{prompt_enc}", timeout=30)
        if r.status_code == 200:
            registrar_api_ativa("Pollinations (gratis)", "texto")
            return r.text
    except Exception as e:
        log.warning(f"Pollinations falhou: {e}")

    return "Todas as APIs indisponiveis no momento. Tentando novamente no proximo ciclo."


def gerar_imagem(prompt):
    """Gera imagem via Pollinations (gratuito, sem limite)"""
    try:
        prompt_enc = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_enc}?width=1280&height=720&nologo=true"
        registrar_api_ativa("Pollinations Images", "imagem")
        return url
    except:
        return None


def gerar_audio(texto):
    """Gera audio via Pollinations TTS (gratuito)"""
    try:
        texto_enc = urllib.parse.quote(texto[:500])
        url = f"https://text.pollinations.ai/{texto_enc}?model=openai-audio&voice=alloy"
        registrar_api_ativa("Pollinations TTS", "audio")
        return url
    except:
        return None


def registrar_api_ativa(nome, tipo):
    if tipo not in estado["apis_ativas"]:
        estado["apis_ativas"][tipo] = []
    if nome not in estado["apis_ativas"][tipo]:
        estado["apis_ativas"][tipo].append(nome)


# ============================================================
# ACOES REAIS DO AGENTE
# ============================================================

def baixar_video(url_youtube):
    """Baixa video do YouTube usando yt-dlp"""
    try:
        resultado = subprocess.run(
            ["yt-dlp", "--no-playlist", "-o", "downloads/%(title)s.%(ext)s", url_youtube],
            capture_output=True, text=True, timeout=300
        )
        if resultado.returncode == 0:
            return {"sucesso": True, "mensagem": "Video baixado com sucesso!", "output": resultado.stdout[-500:]}
        else:
            return {"sucesso": False, "mensagem": resultado.stderr[-500:]}
    except FileNotFoundError:
        return {"sucesso": False, "mensagem": "yt-dlp nao instalado. Adicionando ao requirements..."}
    except Exception as e:
        return {"sucesso": False, "mensagem": str(e)}


def gerar_roteiro(tema, duracao_minutos=5):
    """Gera roteiro completo para video"""
    prompt = f"""Crie um roteiro completo e profissional para um video de {duracao_minutos} minutos sobre: {tema}

Inclua:
- Titulo chamativo
- Introducao (hook nos primeiros 3 segundos)
- Desenvolvimento com pontos principais
- Chamada para acao no final
- Sugestoes de imagens/cenas para cada parte
- Hashtags para redes sociais

Formato profissional, pronto para gravar."""

    return chamar_ia(prompt)


def gerar_descricao_video(titulo, tema):
    """Gera descricao otimizada para YouTube/Instagram"""
    prompt = f"""Crie uma descricao profissional otimizada para SEO para o video:
Titulo: {titulo}
Tema: {tema}

Inclua:
- Descricao principal (200 palavras)
- Palavras-chave relevantes
- Hashtags (30 hashtags)
- Tags para YouTube
- Call-to-action"""

    return chamar_ia(prompt)


def analisar_tendencias():
    """Analisa tendencias de conteudo para M2 Clips"""
    prompt = """Analise as tendencias atuais de conteudo para agencias de video em 2025:

1. Quais tipos de video estao em alta no YouTube, Instagram, TikTok?
2. Quais nichos tem mais demanda por producao de video?
3. Quais formatos (shorts, reels, longform) estao crescendo mais?
4. Que tipo de cliente uma agencia de video deve focar?
5. Quais ferramentas de IA para video sao as mais usadas em agencias?

Seja especifico com dados e exemplos praticos."""

    return chamar_ia(prompt)


def descobrir_apis_gratuitas():
    """Descobre novas APIs gratuitas de IA"""
    prompt = """Liste as melhores APIs gratuitas de IA disponiveis em 2025 para:
- Geracao de texto (LLMs)
- Geracao de imagem
- Geracao de video
- Texto para voz (TTS)
- Pesquisa na web

Para cada API informe:
- Nome
- URL para cadastro
- Limite gratuito
- Se precisa de cartao de credito (sim/nao)
- Qualidade (1-10)

Foque apenas em APIs REALMENTE gratuitas, sem cartao."""

    resultado = chamar_ia(prompt)
    registrar_historico("Descoberta de APIs", resultado[:300])
    return resultado


def registrar_historico(acao, resultado, tipo="info"):
    entrada = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "acao": acao,
        "resultado": resultado[:400],
        "tipo": tipo
    }
    estado["historico"].insert(0, entrada)
    estado["historico"] = estado["historico"][:100]  # mantém ultimas 100
    estado["ultima_acao"] = acao

    # Salva em disco
    try:
        with open("historico.json", "w", encoding="utf-8") as f:
            json.dump(estado["historico"], f, ensure_ascii=False, indent=2)
    except:
        pass


# ============================================================
# CICLO PRINCIPAL DO AGENTE
# ============================================================

def ciclo_agente():
    """Ciclo principal: executa acoes reais a cada 6 horas"""

    # Cria pasta de downloads
    os.makedirs("downloads", exist_ok=True)

    # Carrega historico anterior
    try:
        if os.path.exists("historico.json"):
            with open("historico.json", "r", encoding="utf-8") as f:
                estado["historico"] = json.load(f)
    except:
        pass

    ciclo_num = 0
    while True:
        ciclo_num += 1
        estado["ciclos"] = ciclo_num
        estado["status"] = f"Executando ciclo {ciclo_num}..."
        log.info(f"=== CICLO {ciclo_num} INICIADO ===")

        try:
            # ACAO 1: Analisa tendencias
            estado["status"] = "Analisando tendencias de mercado..."
            log.info("Analisando tendencias...")
            tendencias = analisar_tendencias()
            registrar_historico("Analise de Tendencias", tendencias[:400], "sucesso")
            log.info("Tendencias analisadas!")

            time.sleep(5)

            # ACAO 2: Descobre novas APIs
            estado["status"] = "Descobrindo novas APIs gratuitas..."
            log.info("Buscando APIs gratuitas...")
            apis = descobrir_apis_gratuitas()
            registrar_historico("Descoberta de APIs Gratuitas", apis[:400], "sucesso")
            log.info("APIs descobertas!")

            time.sleep(5)

            # ACAO 3: Gera conteudo automatico
            estado["status"] = "Gerando conteudo para M2 Clips..."
            temas = [
                "como criar videos virais para redes sociais",
                "dicas de edicao de video com IA para iniciantes",
                "como uma agencia de video pode usar IA para escalar",
                "tendencias de video marketing em 2025",
                "como gravar videos profissionais com celular"
            ]
            tema = temas[ciclo_num % len(temas)]
            roteiro = gerar_roteiro(tema, 5)
            registrar_historico(f"Roteiro Gerado: {tema[:50]}", roteiro[:400], "sucesso")
            log.info(f"Roteiro gerado para: {tema}")

            time.sleep(5)

            # ACAO 4: Gera imagem de thumbnail
            estado["status"] = "Gerando thumbnail para video..."
            thumb_url = gerar_imagem(f"thumbnail profissional youtube: {tema}, estilo moderno, cores vibrantes")
            if thumb_url:
                registrar_historico("Thumbnail Gerada", f"URL: {thumb_url[:100]}", "sucesso")
                log.info("Thumbnail gerada!")

        except Exception as e:
            log.error(f"Erro no ciclo {ciclo_num}: {e}")
            registrar_historico("Erro no Ciclo", str(e), "erro")

        estado["status"] = f"Ciclo {ciclo_num} concluido. Proximo em 6 horas."
        log.info(f"Ciclo {ciclo_num} concluido. Aguardando 6 horas...")
        time.sleep(6 * 60 * 60)


# ============================================================
# PAINEL DE CONTROLE WEB
# ============================================================

PAINEL_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>M2 Supreme Agent - Painel de Controle</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; min-height: 100vh; }
  header { background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px 30px; border-bottom: 2px solid #00ff88; display: flex; align-items: center; gap: 15px; }
  header h1 { font-size: 1.6rem; color: #00ff88; }
  header .badge { background: #00ff88; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
  .container { max-width: 1200px; margin: 0 auto; padding: 30px 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
  .card { background: #111122; border: 1px solid #222244; border-radius: 12px; padding: 20px; }
  .card h3 { color: #00ff88; margin-bottom: 15px; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; }
  .stat { font-size: 2rem; font-weight: bold; color: #fff; }
  .stat-label { color: #888; font-size: 0.85rem; margin-top: 5px; }
  .status-badge { display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; }
  .status-ok { background: #003322; color: #00ff88; border: 1px solid #00ff88; }
  .api-tag { display: inline-block; background: #1a1a3e; border: 1px solid #3344aa; color: #8899ff; padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; margin: 3px; }
  .historico { background: #111122; border: 1px solid #222244; border-radius: 12px; padding: 20px; }
  .historico h3 { color: #00ff88; margin-bottom: 15px; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; }
  .entrada { background: #0a0a1a; border-left: 3px solid #00ff88; padding: 12px 15px; margin-bottom: 10px; border-radius: 0 8px 8px 0; }
  .entrada.erro { border-left-color: #ff4444; }
  .entrada .tempo { color: #555; font-size: 0.78rem; }
  .entrada .acao { color: #00ff88; font-weight: bold; margin: 4px 0; font-size: 0.9rem; }
  .entrada.erro .acao { color: #ff4444; }
  .entrada .res { color: #aaa; font-size: 0.82rem; line-height: 1.4; }
  .cmd-box { background: #111122; border: 1px solid #222244; border-radius: 12px; padding: 20px; margin-bottom: 30px; }
  .cmd-box h3 { color: #ff6b35; margin-bottom: 15px; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; }
  .cmd-form { display: flex; gap: 10px; flex-wrap: wrap; }
  .cmd-form input { flex: 1; min-width: 200px; background: #0a0a1a; border: 1px solid #333; color: #fff; padding: 10px 15px; border-radius: 8px; font-size: 0.9rem; }
  .cmd-form button { background: linear-gradient(135deg, #00ff88, #00cc66); color: #000; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 0.9rem; }
  .cmd-form button:hover { opacity: 0.9; }
  .btn-acao { background: #1a1a3e; border: 1px solid #3344aa; color: #8899ff; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin: 4px; font-size: 0.85rem; }
  .btn-acao:hover { background: #2a2a5e; }
  .resultado-cmd { margin-top: 15px; background: #0a0a1a; border: 1px solid #333; border-radius: 8px; padding: 15px; font-size: 0.85rem; line-height: 1.6; white-space: pre-wrap; max-height: 300px; overflow-y: auto; display: none; }
  .info-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #1a1a2e; }
  .info-row:last-child { border-bottom: none; }
  .info-label { color: #888; font-size: 0.85rem; }
  .info-value { color: #fff; font-size: 0.85rem; font-weight: bold; }
</style>
</head>
<body>
<header>
  <div>
    <h1>🤖 M2 SUPREME AGENT</h1>
    <div style="color:#888;font-size:0.85rem;margin-top:4px;">Painel de Controle · 24/7 Autonomo</div>
  </div>
  <span class="badge">● ATIVO</span>
</header>

<div class="container">

  <!-- STATS -->
  <div class="grid">
    <div class="card">
      <h3>Status</h3>
      <span class="status-badge status-ok">● ONLINE 24/7</span>
      <div class="stat-label" style="margin-top:10px;" id="status-texto">Carregando...</div>
    </div>
    <div class="card">
      <h3>Ciclos Executados</h3>
      <div class="stat" id="ciclos">0</div>
      <div class="stat-label">analises automaticas</div>
    </div>
    <div class="card">
      <h3>Acoes Realizadas</h3>
      <div class="stat" id="total-acoes">0</div>
      <div class="stat-label">no historico</div>
    </div>
    <div class="card">
      <h3>Ultima Acao</h3>
      <div style="color:#fff;font-size:0.9rem;margin-top:5px;" id="ultima-acao">-</div>
    </div>
  </div>

  <!-- APIs ATIVAS -->
  <div class="card" style="margin-bottom:20px;">
    <h3>APIs Ativas</h3>
    <div id="apis-ativas"><span style="color:#555;">Carregando...</span></div>
  </div>

  <!-- COMANDOS -->
  <div class="cmd-box">
    <h3>⚡ Comandos Diretos</h3>
    <div style="margin-bottom:15px;">
      <button class="btn-acao" onclick="executarAcao('tendencias')">📈 Analisar Tendencias</button>
      <button class="btn-acao" onclick="executarAcao('apis')">🔌 Descobrir APIs</button>
      <button class="btn-acao" onclick="executarAcao('roteiro')">📝 Gerar Roteiro</button>
      <button class="btn-acao" onclick="executarAcao('thumbnail')">🖼️ Gerar Thumbnail</button>
    </div>
    <div class="cmd-form">
      <input type="text" id="youtube-url" placeholder="Cole URL do YouTube para baixar video..." />
      <button onclick="baixarVideo()">⬇️ Baixar Video</button>
    </div>
    <div class="cmd-form" style="margin-top:10px;">
      <input type="text" id="roteiro-tema" placeholder="Digite tema para gerar roteiro..." />
      <button onclick="gerarRoteiro()">📝 Gerar Roteiro</button>
    </div>
    <div class="cmd-form" style="margin-top:10px;">
      <input type="text" id="img-prompt" placeholder="Descreva a imagem que quer gerar..." />
      <button onclick="gerarImagem()">🖼️ Gerar Imagem</button>
    </div>
    <div class="resultado-cmd" id="resultado-cmd"></div>
  </div>

  <!-- HISTORICO -->
  <div class="historico">
    <h3>📋 Historico de Acoes</h3>
    <div id="historico-lista"><div style="color:#555;padding:20px;">Carregando historico...</div></div>
  </div>

</div>

<script>
async function carregarEstado() {
  try {
    const r = await fetch('/api/estado');
    const d = await r.json();
    
    document.getElementById('ciclos').textContent = d.ciclos || 0;
    document.getElementById('status-texto').textContent = d.status || '-';
    document.getElementById('ultima-acao').textContent = d.ultima_acao || '-';
    document.getElementById('total-acoes').textContent = (d.historico || []).length;
    
    // APIs
    const apis = d.apis_ativas || {};
    let apisHtml = '';
    for (const [tipo, lista] of Object.entries(apis)) {
      apisHtml += `<div style="margin-bottom:8px;"><span style="color:#555;font-size:0.8rem;text-transform:uppercase;">${tipo}:</span> `;
      lista.forEach(a => { apisHtml += `<span class="api-tag">${a}</span>`; });
      apisHtml += '</div>';
    }
    document.getElementById('apis-ativas').innerHTML = apisHtml || '<span style="color:#555;">Nenhuma API ativa ainda</span>';
    
    // Historico
    const hist = d.historico || [];
    if (hist.length === 0) {
      document.getElementById('historico-lista').innerHTML = '<div style="color:#555;padding:20px;">Nenhuma acao registrada ainda.</div>';
    } else {
      document.getElementById('historico-lista').innerHTML = hist.slice(0, 20).map(h => `
        <div class="entrada ${h.tipo === 'erro' ? 'erro' : ''}">
          <div class="tempo">${h.timestamp}</div>
          <div class="acao">${h.acao}</div>
          <div class="res">${h.resultado}</div>
        </div>
      `).join('');
    }
  } catch(e) {
    console.error('Erro ao carregar estado:', e);
  }
}

async function executarAcao(tipo) {
  mostrarResultado('Executando... aguarde.');
  try {
    const r = await fetch('/api/acao', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({acao: tipo})
    });
    const d = await r.json();
    mostrarResultado(d.resultado || d.mensagem || 'Concluido!');
    carregarEstado();
  } catch(e) {
    mostrarResultado('Erro: ' + e.message);
  }
}

async function baixarVideo() {
  const url = document.getElementById('youtube-url').value.trim();
  if (!url) { mostrarResultado('Cole uma URL do YouTube primeiro!'); return; }
  mostrarResultado('Baixando video... pode demorar alguns minutos.');
  try {
    const r = await fetch('/api/acao', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({acao: 'baixar', url: url})
    });
    const d = await r.json();
    mostrarResultado(d.resultado || d.mensagem);
    carregarEstado();
  } catch(e) {
    mostrarResultado('Erro: ' + e.message);
  }
}

async function gerarRoteiro() {
  const tema = document.getElementById('roteiro-tema').value.trim();
  if (!tema) { mostrarResultado('Digite um tema primeiro!'); return; }
  mostrarResultado('Gerando roteiro... aguarde.');
  try {
    const r = await fetch('/api/acao', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({acao: 'roteiro', tema: tema})
    });
    const d = await r.json();
    mostrarResultado(d.resultado);
    carregarEstado();
  } catch(e) {
    mostrarResultado('Erro: ' + e.message);
  }
}

async function gerarImagem() {
  const prompt = document.getElementById('img-prompt').value.trim();
  if (!prompt) { mostrarResultado('Descreva a imagem primeiro!'); return; }
  mostrarResultado('Gerando imagem...');
  try {
    const r = await fetch('/api/acao', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({acao: 'imagem', prompt: prompt})
    });
    const d = await r.json();
    if (d.url) {
      mostrarResultado('Imagem gerada! URL:\n' + d.url + '\n\nAbrindo em nova aba...');
      window.open(d.url, '_blank');
    } else {
      mostrarResultado(d.mensagem || 'Erro ao gerar imagem');
    }
    carregarEstado();
  } catch(e) {
    mostrarResultado('Erro: ' + e.message);
  }
}

function mostrarResultado(texto) {
  const el = document.getElementById('resultado-cmd');
  el.style.display = 'block';
  el.textContent = texto;
}

// Atualiza a cada 10 segundos
carregarEstado();
setInterval(carregarEstado, 10000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/estado":
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(estado, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAINEL_HTML.encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/acao":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            acao = body.get("acao", "")

            resultado = {}

            if acao == "tendencias":
                r = analisar_tendencias()
                registrar_historico("Analise de Tendencias (manual)", r[:400], "sucesso")
                resultado = {"resultado": r}

            elif acao == "apis":
                r = descobrir_apis_gratuitas()
                resultado = {"resultado": r}

            elif acao == "roteiro":
                tema = body.get("tema", "videos virais")
                r = gerar_roteiro(tema)
                registrar_historico(f"Roteiro: {tema[:50]}", r[:400], "sucesso")
                resultado = {"resultado": r}

            elif acao == "imagem":
                prompt = body.get("prompt", "")
                url = gerar_imagem(prompt)
                registrar_historico(f"Imagem gerada: {prompt[:50]}", url or "falhou", "sucesso" if url else "erro")
                resultado = {"url": url, "mensagem": "Imagem gerada!" if url else "Falhou"}

            elif acao == "thumbnail":
                url = gerar_imagem("thumbnail profissional youtube marketing digital 2025 cores vibrantes moderno")
                registrar_historico("Thumbnail gerada", url or "falhou", "sucesso" if url else "erro")
                resultado = {"url": url, "mensagem": "Thumbnail gerada! URL: " + (url or "falhou")}

            elif acao == "baixar":
                url_yt = body.get("url", "")
                r = baixar_video(url_yt)
                registrar_historico(f"Download: {url_yt[:60]}", r["mensagem"], "sucesso" if r["sucesso"] else "erro")
                resultado = {"resultado": r["mensagem"]}

            else:
                resultado = {"mensagem": "Acao desconhecida"}

            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resultado, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def iniciar_servidor():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info(f"Painel rodando na porta {PORT}")
    server.serve_forever()


# ============================================================
# INICIO
# ============================================================
if __name__ == "__main__":
    log.info("🚀 M2 SUPREME AGENT v3.0 INICIANDO...")
    log.info(f"Groq API: {'✅ Configurada' if GROQ_API_KEY else '⚠️ Nao configurada'}")

    t = threading.Thread(target=iniciar_servidor, daemon=True)
    t.start()

    time.sleep(5)
    log.info("Iniciando ciclo principal...")
    ciclo_agente()
