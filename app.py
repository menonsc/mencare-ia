import streamlit as st
import os
import requests
import json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import io
import yaml
from yaml.loader import SafeLoader
import hashlib
import time
from collections import defaultdict
import plotly.express as px
import plotly.graph_objects as go
from supabase_config import get_supabase_client

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações de Autenticação ---
def carregar_config_usuarios():
    """Carrega a configuração de usuários do arquivo config.yaml"""
    try:
        with open('config.yaml') as file:
            return yaml.load(file, Loader=SafeLoader)
    except FileNotFoundError:
        st.error("Arquivo de configuração de usuários não encontrado!")
        return None

def verificar_credenciais(username, password):
    """Verifica se as credenciais do usuário são válidas"""
    config = carregar_config_usuarios()
    if config is None:
        return False
    
    if username in config['credentials']['usernames']:
        stored_password = config['credentials']['usernames'][username]['password']
        # Hash da senha fornecida para comparação
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return stored_password == hashed_password
    return False

def inicializar_autenticacao():
    """Inicializa o estado de autenticação"""
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'login_success' not in st.session_state:
        st.session_state.login_success = False

def login():
    """Interface de login"""
    st.title("🔐 Login Mencare IA")
    
    # Se o login foi bem-sucedido, mostrar mensagem e redirecionar
    if st.session_state.login_success:
        st.success("Login realizado com sucesso!")
        st.session_state.login_success = False
        st.session_state.autenticado = True
        st.rerun()
        return
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            if verificar_credenciais(username, password):
                st.session_state.username = username
                st.session_state.login_success = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos!")

# --- Configurações Iniciais ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Configuração de tokens por plataforma
TOKENS_POR_PLATAFORMA = {
    "Disparo de WhatsApp": 150,
    "Email Marketing": 600,
    "Conteúdo para Redes Sociais (Feed)": 300,
    "Conteúdo para Redes Sociais (Stories)": 200,
    "Copy para SMS": 100       
}

# Adicionar após as configurações iniciais
METRICAS_POR_PLATAFORMA = {
    "Disparo de WhatsApp": {
        "respostas": 0,
        "taxa_conversao": 0.0,
        "total_disparos": 0
    },
    "Email Marketing": {
        "taxa_abertura": 0.0,
        "taxa_clique": 0.0,
        "taxa_conversao": 0.0,
        "total_envios": 0
    },
    "Conteúdo para Redes Sociais (Feed)": {
        "compartilhamentos": 0,
        "likes": 0,
        "comentarios": 0,
        "alcance": 0
    },
    "Conteúdo para Redes Sociais (Stories)": {
        "visualizacoes": 0,
        "respostas": 0,
        "cliques": 0,
        "alcance": 0
    },
    "Copy para SMS": {
        "taxa_clique": 0.0,
        "taxa_conversao": 0.0,
        "total_envios": 0
    }
}

# Adicionar após as configurações iniciais
TAGS_PREDEFINIDAS = {
    "Tipo de Negócio": [
        "E-commerce",
        "Serviços",
        "Produtos Físicos",
        "Digital",
        "B2B",
        "B2C"
    ],
    "Setor": [
        "Saúde",
        "Educação",
        "Tecnologia",
        "Moda",
        "Alimentação",
        "Finanças",
        "Imobiliário",
        "Outros"
    ],
    "Objetivo": [
        "Vendas",
        "Leads",
        "Engajamento",
        "Branding",
        "Fidelização",
        "Educação"
    ],
    "Público": [
        "Jovens",
        "Adultos",
        "Profissionais",
        "Empresários",
        "Estudantes",
        "Famílias"
    ]
}

# Verificar se as configurações essenciais estão presentes
if not OPENAI_API_KEY:
    st.error("Chave da API da OpenAI não configurada. Verifique o arquivo .env.")
    st.stop()
if not (SUPABASE_URL and SUPABASE_KEY):
    st.warning("Configurações do Supabase incompletas. A funcionalidade de salvar no banco de dados pode não funcionar.")

# Inicializar cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Inicializar cliente Supabase
supabase = get_supabase_client()

# Inicializar autenticação
inicializar_autenticacao()

# --- Funções Auxiliares ---

def gerar_copy_openai(plataforma, objetivo, publico_alvo, produto_servico, tom_de_voz, cta, informacoes_adicionais=""):
    # Obter o limite de tokens para a plataforma selecionada
    max_tokens = TOKENS_POR_PLATAFORMA.get(plataforma, 300)
    
    # Criar barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Atualizar status - Preparando prompt
        status_text.text("🔄 Preparando prompt...")
        progress_bar.progress(10)
        time.sleep(0.5)  # Pequena pausa para feedback visual
        
        prompt = f"""
        Você é um copywriter especialista em marketing digital com mais de 20 anos de experiência.
        Sua tarefa é gerar uma copy persuasiva e eficaz para a plataforma especificada.
        IMPORTANTE: Mantenha a copy dentro do limite de {max_tokens} tokens.

        Plataforma: {plataforma}
        Objetivo da Copy: {objetivo}
        Público-Alvo: {publico_alvo}
        Produto/Serviço a ser promovido: {produto_servico}
        Tom de Voz desejado: {tom_de_voz}
        Call to Action (CTA): {cta}
        {f"Informações Adicionais: {informacoes_adicionais}" if informacoes_adicionais else ""}

        Instruções específicas para a plataforma '{plataforma}':
        """

        # Atualizar status - Configurando modelo
        status_text.text("⚙️ Configurando modelo de IA...")
        progress_bar.progress(30)
        time.sleep(0.5)

        if plataforma == "Disparo de WhatsApp":
            prompt += """
            - Seja breve, direto e pessoal.
            - Use emojis com moderação para aumentar o engajamento.
            - Ideal para mensagens curtas e impacto rápido.
            - Inicie de forma amigável.
            - Deixe o CTA claro e fácil de seguir.
            - Considere o uso de gatilhos mentais como urgência ou escassez, se aplicável.
            """
        elif plataforma == "Email Marketing":
            prompt += """
            - Assunto do email: Crie um assunto curto, chamativo e que gere curiosidade.
            - Corpo do email:
                - Comece com uma saudação personalizada, se possível.
                - Desenvolva o problema ou necessidade do público-alvo.
                - Apresente o produto/serviço como a solução.
                - Destaque os principais benefícios.
                - Use parágrafos curtos e boa formatação (negrito, listas).
                - O CTA deve ser claro e visível (pode ser um link ou botão).
            - Pode ser mais longo que outras plataformas, mas mantenha o foco.
            """
        elif plataforma == "Conteúdo para Redes Sociais (Feed)":
            prompt += """
            - Adapte a linguagem para a rede social específica (ex: Instagram mais visual, LinkedIn mais profissional).
            - Use hashtags relevantes (sugira 3-5 hashtags).
            - Incentive o engajamento (perguntas, enquetes, pedir comentários).
            - Imagens/vídeos são importantes, mas a copy precisa ser atrativa por si só.
            - Pode contar uma pequena história ou dar uma dica rápida.
            """
        elif plataforma == "Conteúdo para Redes Sociais (Stories)":
            prompt += """
            - Formato curto e dinâmico.
            - Use texto conciso e chamativo.
            - Ideal para enquetes, perguntas rápidas, "arrasta para cima".
            - Pode ser mais informal.
            - O CTA deve ser imediato.
            """
        elif plataforma == "Copy para SMS":
            prompt += """
            - Extremamente curto e objetivo (limite de caracteres, geralmente 160).
            - CTA direto e, se possível, com link encurtado.
            - Use abreviações com cautela para não prejudicar a clareza.
            - Ideal para lembretes, promoções rápidas ou alertas.
            """

        prompt += "\nGere a copy abaixo:\n"

        # Atualizar status - Gerando copy
        status_text.text("🤖 Gerando copy com IA...")
        progress_bar.progress(50)
        time.sleep(0.5)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Você é um copywriter especialista em marketing digital."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens
        )

        # Rastrear consumo de tokens
        tokens_consumidos = response.usage.total_tokens
        salvar_consumo_tokens(tokens_consumidos, "copy")
        
        # Atualizar status - Finalizando
        status_text.text("✨ Finalizando e formatando copy...")
        progress_bar.progress(90)
        time.sleep(0.5)

        copy_gerada = response.choices[0].message.content.strip()
        
        # Concluído
        status_text.text("✅ Copy gerada com sucesso!")
        progress_bar.progress(100)
        time.sleep(0.5)
        
        # Limpar elementos de progresso
        progress_bar.empty()
        status_text.empty()
        
        return copy_gerada
    except Exception as e:
        # Em caso de erro
        status_text.text("❌ Erro ao gerar copy")
        progress_bar.progress(0)
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        st.error(f"Erro ao contatar a OpenAI: {e}")
        return None

def salvar_no_supabase(data_to_save):
    """Salva uma copy no Supabase"""
    try:
        # Adicionar usuário_id se disponível
        if 'username' in st.session_state:
            data_to_save['usuario_id'] = st.session_state.username

        # Formatar dados para o Supabase
        payload = {
            "plataforma": data_to_save.get("plataforma"),
            "objetivo": data_to_save.get("objetivo"),
            "publico_alvo": data_to_save.get("publico_alvo"),
            "produto_servico": data_to_save.get("produto_servico"),
            "tom_de_voz": data_to_save.get("tom_de_voz"),
            "cta": data_to_save.get("cta"),
            "copy_gerada": data_to_save.get("copy_gerada"),
            "data_geracao": datetime.now().isoformat()
        }

        # Remover campos None
        payload = {k: v for k, v in payload.items() if v is not None}

        # Salvar no Supabase
        response = supabase.table('copies').insert(payload).execute()
        
        if response.data:
            st.success("Copy salva com sucesso no Supabase!")
            return True
        else:
            st.error("Erro ao salvar copy no Supabase.")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar no Supabase: {e}")
        return False

def salvar_analise_leads(analise_data):
    """Salva a análise de leads no Supabase"""
    try:
        # Adicionar usuário_id se disponível
        if 'username' in st.session_state:
            analise_data['usuario_id'] = st.session_state.username

        # Formatar dados para o Supabase
        payload = {
            "plataforma": analise_data.get("plataforma"),
            "objetivo": analise_data.get("objetivo"),
            "total_leads": analise_data.get("total_leads"),
            "colunas": json.dumps(analise_data.get("colunas", [])),
            "analise": analise_data.get("analise"),
            "tempo_processamento": analise_data.get("tempo_processamento"),
            "resumo_estatistico": json.dumps(analise_data.get("resumo_estatistico", {}))
        }

        # Salvar no Supabase
        response = supabase.table('analises_leads').insert(payload).execute()
        
        if response.data:
            # Salvar tags se existirem
            if 'tags' in analise_data and analise_data['tags']:
                for tag in analise_data['tags']:
                    tag_data = {
                        "analise_id": response.data[0]['id'],
                        "categoria": "Personalizada",
                        "tag": tag,
                        "usuario_id": st.session_state.username
                    }
                    supabase.table('tags').insert(tag_data).execute()
            
            return True
        else:
            st.error("Erro ao salvar análise no Supabase.")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar análise: {e}")
        return False

def atualizar_tags_analise(analise_id, novas_tags):
    """Atualiza as tags de uma análise específica"""
    try:
        filename = f"historico/analises_{st.session_state.username}.json"
        
        if not os.path.exists(filename):
            st.error("Nenhuma análise encontrada.")
            return False
        
        with open(filename, 'r', encoding='utf-8') as f:
            historico = json.load(f)
        
        # Encontrar e atualizar a análise
        for analise in historico:
            if analise['id'] == analise_id:
                analise['tags'] = novas_tags
                break
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=4)
        
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar tags: {e}")
        return False

def gerar_insights_com_tags(analise, tags):
    """Gera insights baseados nas tags da análise"""
    try:
        # Carregar análises anteriores com tags similares
        filename = f"historico/analises_{st.session_state.username}.json"
        insights = []
        
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                historico = json.load(f)
            
            # Filtrar análises com tags similares
            analises_similares = [
                a for a in historico 
                if a['id'] != analise['id'] and 
                any(tag in a.get('tags', []) for tag in tags)
            ]
            
            if analises_similares:
                # Agrupar insights por tipo de tag
                insights_por_tag = {}
                for tag in tags:
                    insights_por_tag[tag] = []
                
                for analise_similar in analises_similares:
                    for tag in tags:
                        if tag in analise_similar.get('tags', []):
                            insights_por_tag[tag].append({
                                'data': analise_similar['data'],
                                'plataforma': analise_similar['plataforma'],
                                'objetivo': analise_similar['objetivo'],
                                'analise': analise_similar['analise']
                            })
                
                # Formatar insights
                for tag, analises in insights_por_tag.items():
                    if analises:
                        insights.append(f"\n### Insights baseados na tag '{tag}':")
                        for analise_similar in analises[:3]:  # Limitar a 3 insights por tag
                            insights.append(f"""
**Data:** {analise_similar['data']}
**Plataforma:** {analise_similar['plataforma']}
**Objetivo:** {analise_similar['objetivo']}
**Análise:** {analise_similar['analise']}
---""")
        
        return "\n".join(insights) if insights else "Nenhum insight similar encontrado."
    except Exception as e:
        st.error(f"Erro ao gerar insights: {e}")
        return "Erro ao gerar insights."

def carregar_historico_analises():
    """Carrega o histórico de análises do usuário atual"""
    try:
        filename = f"historico/analises_{st.session_state.username}.json"
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return []

def salvar_feedback(analise_id, feedback_data):
    """Salva o feedback no Supabase"""
    try:
        # Adicionar usuário_id se disponível
        if 'username' in st.session_state:
            feedback_data['usuario_id'] = st.session_state.username

        # Formatar dados para o Supabase
        payload = {
            "analise_id": analise_id,
            "pontos_positivos": feedback_data.get("pontos_positivos"),
            "pontos_melhorar": feedback_data.get("pontos_melhorar"),
            "nota": feedback_data.get("nota"),
            "editado": False,
            "historico_edicoes": json.dumps([])
        }

        # Salvar no Supabase
        response = supabase.table('feedback').insert(payload).execute()
        
        if response.data:
            return True
        else:
            st.error("Erro ao salvar feedback no Supabase.")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar feedback: {e}")
        return False

def editar_feedback(analise_id, novo_feedback):
    """Edita um feedback existente"""
    try:
        filename = f"feedback/feedback_{st.session_state.username}.json"
        
        if not os.path.exists(filename):
            st.error("Nenhum feedback encontrado para editar.")
            return False
        
        with open(filename, 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)
        
        if analise_id not in feedbacks:
            st.error("Feedback não encontrado.")
            return False
        
        # Salvar versão anterior no histórico
        feedback_anterior = feedbacks[analise_id].copy()
        feedback_anterior["timestamp_edicao"] = datetime.now().isoformat()
        
        feedbacks[analise_id]["historico_edicoes"].append(feedback_anterior)
        
        # Atualizar feedback
        feedbacks[analise_id].update(novo_feedback)
        feedbacks[analise_id]["editado"] = True
        feedbacks[analise_id]["ultima_edicao"] = datetime.now().isoformat()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(feedbacks, f, ensure_ascii=False, indent=4)
        
        return True
    except Exception as e:
        st.error(f"Erro ao editar feedback: {e}")
        return False

def salvar_metricas_plataforma(plataforma, metricas_data):
    """Salva métricas específicas da plataforma no Supabase"""
    try:
        # Adicionar usuário_id se disponível
        if 'username' in st.session_state:
            metricas_data['usuario_id'] = st.session_state.username

        # Formatar dados para o Supabase
        payload = {
            "plataforma": plataforma,
            "metricas": json.dumps(metricas_data),
            "data": datetime.now().isoformat()
        }

        # Salvar no Supabase
        response = supabase.table('metricas_plataforma').insert(payload).execute()
        
        if response.data:
            return True
        else:
            st.error("Erro ao salvar métricas no Supabase.")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar métricas da plataforma: {e}")
        return False

def analisar_leads_csv(df, plataforma, objetivo):
    """
    Analisa os leads do CSV e gera insights usando a IA
    """
    try:
        # Criar barra de progresso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        tempo_inicio = time.time()
        
        # Atualizar status - Preparando dados
        status_text.text("🔄 Preparando dados para análise...")
        progress_bar.progress(10)
        time.sleep(0.5)
        
        # Carregar feedbacks anteriores para melhorar a análise
        feedbacks = []
        if os.path.exists(f"feedback/feedback_{st.session_state.username}.json"):
            with open(f"feedback/feedback_{st.session_state.username}.json", 'r', encoding='utf-8') as f:
                feedbacks = list(json.load(f).values())
        
        # Atualizar status - Processando dados
        status_text.text("📊 Processando dados dos leads...")
        progress_bar.progress(30)
        time.sleep(0.5)
        
        # Otimizar dados para análise
        # 1. Selecionar apenas colunas relevantes
        colunas_relevantes = df.columns[:9]  # Limitar a 9 colunas
        df_otimizado = df[colunas_relevantes].copy()
        
        # 2. Limitar número de linhas para análise
        max_linhas = 100  # Limitar a 100 linhas para análise
        if len(df_otimizado) > max_linhas:
            df_otimizado = df_otimizado.sample(n=max_linhas, random_state=42)
        
        # 3. Preparar resumo estatístico
        resumo_estatistico = {
            "total_leads": len(df),
            "colunas_analisadas": list(colunas_relevantes),
            "amostra_analisada": len(df_otimizado),
            "estatisticas": {}
        }
        
        # Adicionar estatísticas básicas para cada coluna
        for coluna in colunas_relevantes:
            if df_otimizado[coluna].dtype in ['int64', 'float64']:
                resumo_estatistico["estatisticas"][coluna] = {
                    "media": df_otimizado[coluna].mean(),
                    "mediana": df_otimizado[coluna].median(),
                    "min": df_otimizado[coluna].min(),
                    "max": df_otimizado[coluna].max()
                }
            else:
                # Para colunas categóricas, mostrar top 5 valores mais frequentes
                resumo_estatistico["estatisticas"][coluna] = {
                    "valores_mais_frequentes": df_otimizado[coluna].value_counts().head().to_dict()
                }
        
        # Converter o DataFrame otimizado para string
        df_str = df_otimizado.to_string()
        
        # Preparar contexto de aprendizado baseado em feedbacks anteriores
        contexto_aprendizado = ""
        if feedbacks:
            contexto_aprendizado = """
            Baseado em feedbacks anteriores dos usuários, considere:
            """
            for feedback in feedbacks[:3]:  # Limitar a 3 feedbacks mais recentes
                if feedback.get('pontos_positivos'):
                    contexto_aprendizado += f"\n- Pontos positivos anteriores: {feedback['pontos_positivos']}"
                if feedback.get('pontos_melhorar'):
                    contexto_aprendizado += f"\n- Pontos a melhorar: {feedback['pontos_melhorar']}"
        
        # Atualizar status - Configurando análise
        status_text.text("⚙️ Configurando análise com IA...")
        progress_bar.progress(50)
        time.sleep(0.5)
        
        prompt = f"""
        Você é um especialista em análise de dados e marketing digital.
        Analise os seguintes dados de leads e forneça insights relevantes para {plataforma} com o objetivo de {objetivo}.

        {contexto_aprendizado}

        Resumo dos dados:
        - Total de leads: {resumo_estatistico['total_leads']}
        - Amostra analisada: {resumo_estatistico['amostra_analisada']}
        - Colunas analisadas: {', '.join(resumo_estatistico['colunas_analisadas'])}

        Estatísticas básicas:
        {json.dumps(resumo_estatistico['estatisticas'], indent=2)}

        Dados da amostra:
        {df_str}

        Por favor, forneça:
        1. Análise geral dos dados
        2. Insights específicos para {plataforma}
        3. Recomendações de estratégia para atingir o objetivo de {objetivo}
        4. Sugestões de segmentação dos leads
        5. Possíveis abordagens personalizadas

        Mantenha a análise clara e objetiva, focando em insights acionáveis.
        """

        # Atualizar status - Gerando análise
        status_text.text("🤖 Gerando análise com IA...")
        progress_bar.progress(70)
        time.sleep(0.5)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Você é um especialista em análise de dados e marketing digital."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800 
        )
        
        # Rastrear consumo de tokens
        tokens_consumidos = response.usage.total_tokens
        salvar_consumo_tokens(tokens_consumidos, "analise")
        
        # Atualizar status - Finalizando
        status_text.text("✨ Finalizando e formatando análise...")
        progress_bar.progress(90)
        time.sleep(0.5)
        
        analise = response.choices[0].message.content.strip()
        analise_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(analise.encode()).hexdigest()[:8]}"
        
        # Calcular tempo de processamento
        tempo_processamento = time.time() - tempo_inicio
        
        # Preparar dados para salvar no histórico
        analise_data = {
            "id": analise_id,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "plataforma": plataforma,
            "objetivo": objetivo,
            "total_leads": len(df),
            "colunas": list(df.columns),
            "analise": analise,
            "tempo_processamento": tempo_processamento,
            "resumo_estatistico": resumo_estatistico
        }
        
        # Salvar no histórico
        salvar_analise_leads(analise_data)
        
        # Salvar métricas
        metricas_data = {
            "analise": {
                "data": analise_data["data"],
                "plataforma": plataforma,
                "objetivo": objetivo,
                "total_leads": len(df),
                "tempo_processamento": tempo_processamento
            }
        }
        salvar_metricas(metricas_data)
        
        # Concluído
        status_text.text("✅ Análise concluída com sucesso!")
        progress_bar.progress(100)
        time.sleep(0.5)
        
        # Limpar elementos de progresso
        progress_bar.empty()
        status_text.empty()
        
        return analise, analise_id
    except Exception as e:
        # Em caso de erro
        status_text.text("❌ Erro ao analisar leads")
        progress_bar.progress(0)
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        st.error(f"Erro ao analisar os leads: {e}")
        return None, None

def mostrar_historico_analises():
    """Mostra o histórico de análises com opções de feedback e métricas"""
    st.subheader("📚 Histórico de Análises")
    
    # Filtro de tags
    st.sidebar.subheader("🔍 Filtros")
    tags_selecionadas = []
    
    for categoria, tags in TAGS_PREDEFINIDAS.items():
        st.sidebar.write(f"**{categoria}:**")
        for tag in tags:
            # Criar uma chave única combinando categoria e tag
            chave_unica = f"filter_{categoria}_{tag}".replace(" ", "_").lower()
            if st.sidebar.checkbox(tag, key=chave_unica):
                tags_selecionadas.append(tag)
    
    historico_analises = carregar_historico_analises()
    
    if not historico_analises:
        st.info("Nenhuma análise realizada ainda.")
    else:
        # Filtrar análises por tags selecionadas
        if tags_selecionadas:
            historico_analises = [
                analise for analise in historico_analises
                if any(tag in analise.get('tags', []) for tag in tags_selecionadas)
            ]
        
        for idx, analise in enumerate(reversed(historico_analises)):
            with st.expander(f"Análise #{len(historico_analises) - idx} - {analise['plataforma']} - {analise['data']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Plataforma:** {analise['plataforma']}")
                    st.write(f"**Objetivo:** {analise['objetivo']}")
                    st.write(f"**Data:** {analise['data']}")
                    st.write(f"**Total de Leads:** {analise['total_leads']}")
                    st.write("**Colunas Analisadas:**")
                    for col in analise['colunas']:
                        st.write(f"- {col}")
                
                with col2:
                    # Gerenciamento de Tags
                    st.write("**Tags:**")
                    tags_atuais = analise.get('tags', [])
                    
                    # Mostrar tags atuais
                    if tags_atuais:
                        for tag in tags_atuais:
                            st.write(f"🏷️ {tag}")
                    
                    # Formulário para adicionar novas tags
                    with st.form(f"tags_form_{idx}"):
                        novas_tags = []
                        for categoria, tags in TAGS_PREDEFINIDAS.items():
                            st.write(f"**{categoria}:**")
                            for tag in tags:
                                # Criar uma chave única para cada checkbox de tag
                                chave_unica = f"tag_{idx}_{categoria}_{tag}".replace(" ", "_").lower()
                                if st.checkbox(tag, key=chave_unica, value=tag in tags_atuais):
                                    novas_tags.append(tag)
                        
                        if st.form_submit_button("Atualizar Tags"):
                            if atualizar_tags_analise(analise['id'], novas_tags):
                                st.success("Tags atualizadas com sucesso!")
                                st.rerun()
                
                st.write("**Análise:**")
                st.markdown(analise['analise'])
                
                # Mostrar insights baseados nas tags
                if analise.get('tags'):
                    st.write("**💡 Insights Relacionados:**")
                    insights = gerar_insights_com_tags(analise, analise['tags'])
                    st.markdown(insights)
                
                # Seção de Feedback
                st.subheader("💭 Feedback da Análise")
                feedback = carregar_feedback(analise['id'])
                
                if feedback:
                    st.write("**Feedback Atual:**")
                    st.write(f"Nota: {'⭐' * feedback['nota']}")
                    if feedback['pontos_positivos']:
                        st.write(f"**Pontos Positivos:** {feedback['pontos_positivos']}")
                    if feedback['pontos_melhorar']:
                        st.write(f"**Pontos a Melhorar:** {feedback['pontos_melhorar']}")
                    
                    if feedback.get('editado'):
                        st.write(f"**Última edição:** {feedback['ultima_edicao']}")
                    
                    # Botão para editar feedback
                    if st.button("✏️ Editar Feedback", key=f"edit_feedback_{idx}"):
                        with st.form(f"edit_feedback_form_{idx}"):
                            novos_pontos_positivos = st.text_area(
                                "Pontos Positivos:",
                                value=feedback['pontos_positivos'],
                                key=f"edit_pos_{idx}"
                            )
                            novos_pontos_melhorar = st.text_area(
                                "Pontos a Melhorar:",
                                value=feedback['pontos_melhorar'],
                                key=f"edit_neg_{idx}"
                            )
                            nova_nota = st.slider(
                                "Nota:",
                                1, 5,
                                value=feedback['nota'],
                                key=f"edit_nota_{idx}"
                            )
                            if st.form_submit_button("Salvar Alterações"):
                                novo_feedback = {
                                    "pontos_positivos": novos_pontos_positivos,
                                    "pontos_melhorar": novos_pontos_melhorar,
                                    "nota": nova_nota
                                }
                                if editar_feedback(analise['id'], novo_feedback):
                                    st.success("Feedback atualizado com sucesso!")
                                    st.rerun()
                else:
                    # Formulário para novo feedback
                    with st.form(f"feedback_form_{idx}"):
                        pontos_positivos = st.text_area("Pontos Positivos:", 
                            placeholder="O que você achou mais útil nesta análise?")
                        pontos_melhorar = st.text_area("Pontos a Melhorar:", 
                            placeholder="O que poderia ser melhorado nesta análise?")
                        nota = st.slider("Nota da Análise:", 1, 5, 3)
                        if st.form_submit_button("Enviar Feedback"):
                            feedback_data = {
                                "pontos_positivos": pontos_positivos,
                                "pontos_melhorar": pontos_melhorar,
                                "nota": nota
                            }
                            if salvar_feedback(analise['id'], feedback_data):
                                st.success("Feedback enviado com sucesso!")
                                st.rerun()
                
                # Seção de Métricas da Plataforma
                st.subheader("📊 Métricas da Plataforma")
                with st.form(f"metricas_form_{idx}"):
                    st.write(f"**Métricas para {analise['plataforma']}:**")
                    
                    if analise['plataforma'] == "Disparo de WhatsApp":
                        respostas = st.number_input("Número de Respostas:", min_value=0)
                        conversoes = st.number_input("Número de Conversões:", min_value=0)
                        total_disparos = st.number_input("Total de Disparos:", min_value=0)
                        
                        if st.form_submit_button("Salvar Métricas"):
                            metricas = {
                                "respostas": respostas,
                                "taxa_conversao": (conversoes / total_disparos * 100) if total_disparos > 0 else 0,
                                "total_disparos": total_disparos
                            }
                            if salvar_metricas_plataforma(analise['plataforma'], metricas):
                                st.success("Métricas salvas com sucesso!")
                    
                    elif analise['plataforma'] == "Email Marketing":
                        taxa_abertura = st.number_input("Taxa de Abertura (%):", min_value=0.0, max_value=100.0)
                        taxa_clique = st.number_input("Taxa de Clique (%):", min_value=0.0, max_value=100.0)
                        taxa_conversao = st.number_input("Taxa de Conversão (%):", min_value=0.0, max_value=100.0)
                        total_envios = st.number_input("Total de Envios:", min_value=0)
                        
                        if st.form_submit_button("Salvar Métricas"):
                            metricas = {
                                "taxa_abertura": taxa_abertura,
                                "taxa_clique": taxa_clique,
                                "taxa_conversao": taxa_conversao,
                                "total_envios": total_envios
                            }
                            if salvar_metricas_plataforma(analise['plataforma'], metricas):
                                st.success("Métricas salvas com sucesso!")
                    
                    elif analise['plataforma'] == "Conteúdo para Redes Sociais (Feed)":
                        compartilhamentos = st.number_input("Compartilhamentos:", min_value=0)
                        likes = st.number_input("Likes:", min_value=0)
                        comentarios = st.number_input("Comentários:", min_value=0)
                        alcance = st.number_input("Alcance:", min_value=0)
                        
                        if st.form_submit_button("Salvar Métricas"):
                            metricas = {
                                "compartilhamentos": compartilhamentos,
                                "likes": likes,
                                "comentarios": comentarios,
                                "alcance": alcance
                            }
                            if salvar_metricas_plataforma(analise['plataforma'], metricas):
                                st.success("Métricas salvas com sucesso!")
                    
                    elif analise['plataforma'] == "Conteúdo para Redes Sociais (Stories)":
                        visualizacoes = st.number_input("Visualizações:", min_value=0)
                        respostas = st.number_input("Respostas:", min_value=0)
                        cliques = st.number_input("Cliques:", min_value=0)
                        alcance = st.number_input("Alcance:", min_value=0)
                        
                        if st.form_submit_button("Salvar Métricas"):
                            metricas = {
                                "visualizacoes": visualizacoes,
                                "respostas": respostas,
                                "cliques": cliques,
                                "alcance": alcance
                            }
                            if salvar_metricas_plataforma(analise['plataforma'], metricas):
                                st.success("Métricas salvas com sucesso!")
                    
                    elif analise['plataforma'] == "Copy para SMS":
                        taxa_clique = st.number_input("Taxa de Clique (%):", min_value=0.0, max_value=100.0)
                        taxa_conversao = st.number_input("Taxa de Conversão (%):", min_value=0.0, max_value=100.0)
                        total_envios = st.number_input("Total de Envios:", min_value=0)
                        
                        if st.form_submit_button("Salvar Métricas"):
                            metricas = {
                                "taxa_clique": taxa_clique,
                                "taxa_conversao": taxa_conversao,
                                "total_envios": total_envios
                            }
                            if salvar_metricas_plataforma(analise['plataforma'], metricas):
                                st.success("Métricas salvas com sucesso!")
                
                # Botão para copiar a análise
                if st.button("📋 Copiar Análise", key=f"copy_hist_{idx}"):
                    st.code(analise['analise'])
                    st.success("Análise copiada para a área de transferência!")

def carregar_feedback(analise_id):
    """Carrega o feedback para uma análise específica"""
    try:
        filename = f"feedback/feedback_{st.session_state.username}.json"
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                feedbacks = json.load(f)
                return feedbacks.get(analise_id, None)
        return None
    except Exception as e:
        st.error(f"Erro ao carregar feedback: {e}")
        return None

def carregar_metricas():
    """Carrega as métricas de performance do usuário"""
    try:
        filename = f"metricas/metricas_{st.session_state.username}.json"
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        st.error(f"Erro ao carregar métricas: {e}")
        return None

def carregar_metricas_plataforma():
    """Carrega as métricas específicas da plataforma"""
    try:
        filename = f"metricas/metricas_plataforma_{st.session_state.username}.json"
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        st.error(f"Erro ao carregar métricas da plataforma: {e}")
        return None

def carregar_consumo_tokens():
    """Carrega o consumo de tokens do usuário"""
    try:
        filename = f"metricas/tokens_{st.session_state.username}.json"
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "total_tokens": 0,
            "historico": [],
            "por_operacao": {
                "copy": 0,
                "analise": 0
            }
        }
    except Exception as e:
        st.error(f"Erro ao carregar consumo de tokens: {e}")
        return None

def gerar_dashboard():
    """Gera o dashboard com métricas e visualizações importantes"""
    st.subheader("📊 Dashboard Geral")
    
    # Carregar dados
    metricas = carregar_metricas()
    metricas_plataforma = carregar_metricas_plataforma()
    historico_analises = carregar_historico_analises()
    consumo_tokens = carregar_consumo_tokens()
    
    if not metricas and not metricas_plataforma and not historico_analises:
        st.info("Nenhum dado disponível para exibir no dashboard. Comece a usar o sistema para gerar métricas.")
        return
    
    # Layout em colunas para métricas principais
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_analises = len(historico_analises) if historico_analises else 0
        st.metric("Total de Análises", total_analises)
    
    with col2:
        total_feedback = metricas.get('total_feedback', 0) if metricas else 0
        st.metric("Total de Feedback", total_feedback)
    
    with col3:
        media_notas = metricas.get('media_notas', 0) if metricas else 0
        st.metric("Média de Notas", f"{media_notas:.1f} ⭐")
    
    with col4:
        tempo_medio = metricas.get('tempo_medio_analise', 0) if metricas else 0
        st.metric("Tempo Médio de Análise", f"{tempo_medio:.1f}s")
    
    with col5:
        total_tokens = consumo_tokens.get('total_tokens', 0) if consumo_tokens else 0
        st.metric("Total de Tokens", f"{total_tokens:,}")
    
    # Adicionar seção de consumo de tokens
    st.subheader("🔢 Consumo de Tokens")
    col1, col2 = st.columns(2)
    
    with col1:
        if consumo_tokens:
            # Gráfico de pizza para distribuição por operação
            fig = px.pie(
                values=[
                    consumo_tokens['por_operacao']['copy'],
                    consumo_tokens['por_operacao']['analise']
                ],
                names=['Copy', 'Análise'],
                title='Distribuição de Tokens por Operação'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if consumo_tokens and consumo_tokens['historico']:
            # Preparar dados para o gráfico de linha
            historico = consumo_tokens['historico'][-10:]  # Últimas 10 operações
            datas = [datetime.strptime(h['data'], "%d/%m/%Y %H:%M:%S") for h in historico]
            tokens = [h['tokens'] for h in historico]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=datas,
                y=tokens,
                mode='lines+markers',
                name='Tokens Consumidos'
            ))
            
            fig.update_layout(
                title='Consumo de Tokens nas Últimas Operações',
                xaxis_title='Data',
                yaxis_title='Tokens',
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Gráficos e análises
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Análises por Plataforma")
        if historico_analises:
            # Preparar dados para o gráfico
            plataformas = {}
            for analise in historico_analises:
                plataforma = analise['plataforma']
                plataformas[plataforma] = plataformas.get(plataforma, 0) + 1
            
            # Criar gráfico de barras
            fig = px.bar(
                x=list(plataformas.keys()),
                y=list(plataformas.values()),
                labels={'x': 'Plataforma', 'y': 'Quantidade'},
                title='Distribuição de Análises por Plataforma'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Objetivos Mais Comuns")
        if historico_analises:
            # Preparar dados para o gráfico
            objetivos = {}
            for analise in historico_analises:
                objetivo = analise['objetivo']
                objetivos[objetivo] = objetivos.get(objetivo, 0) + 1
            
            # Criar gráfico de pizza
            fig = px.pie(
                values=list(objetivos.values()),
                names=list(objetivos.keys()),
                title='Distribuição de Objetivos'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Métricas por Plataforma
    st.subheader("📊 Métricas por Plataforma")
    if metricas_plataforma:
        for plataforma, metricas in metricas_plataforma.items():
            with st.expander(f"📱 {plataforma}"):
                col1, col2, col3, col4 = st.columns(4)
                
                if plataforma == "Disparo de WhatsApp":
                    with col1:
                        st.metric("Respostas", metricas.get('respostas', 0))
                    with col2:
                        st.metric("Taxa de Conversão", f"{metricas.get('taxa_conversao', 0):.1f}%")
                    with col3:
                        st.metric("Total de Disparos", metricas.get('total_disparos', 0))
                
                elif plataforma == "Email Marketing":
                    with col1:
                        st.metric("Taxa de Abertura", f"{metricas.get('taxa_abertura', 0):.1f}%")
                    with col2:
                        st.metric("Taxa de Clique", f"{metricas.get('taxa_clique', 0):.1f}%")
                    with col3:
                        st.metric("Taxa de Conversão", f"{metricas.get('taxa_conversao', 0):.1f}%")
                    with col4:
                        st.metric("Total de Envios", metricas.get('total_envios', 0))
                
                elif plataforma == "Conteúdo para Redes Sociais (Feed)":
                    with col1:
                        st.metric("Compartilhamentos", metricas.get('compartilhamentos', 0))
                    with col2:
                        st.metric("Likes", metricas.get('likes', 0))
                    with col3:
                        st.metric("Comentários", metricas.get('comentarios', 0))
                    with col4:
                        st.metric("Alcance", metricas.get('alcance', 0))
                
                elif plataforma == "Conteúdo para Redes Sociais (Stories)":
                    with col1:
                        st.metric("Visualizações", metricas.get('visualizacoes', 0))
                    with col2:
                        st.metric("Respostas", metricas.get('respostas', 0))
                    with col3:
                        st.metric("Cliques", metricas.get('cliques', 0))
                    with col4:
                        st.metric("Alcance", metricas.get('alcance', 0))
                
                elif plataforma == "Copy para SMS":
                    with col1:
                        st.metric("Taxa de Clique", f"{metricas.get('taxa_clique', 0):.1f}%")
                    with col2:
                        st.metric("Taxa de Conversão", f"{metricas.get('taxa_conversao', 0):.1f}%")
                    with col3:
                        st.metric("Total de Envios", metricas.get('total_envios', 0))
    
    # Análise Temporal
    st.subheader("⏳ Análise Temporal")
    if historico_analises:
        # Preparar dados para o gráfico
        datas = []
        for analise in historico_analises:
            try:
                data = datetime.strptime(analise['data'], "%d/%m/%Y %H:%M:%S")
                datas.append(data)
            except:
                continue
        
        if datas:
            # Criar gráfico de linha
            datas.sort()
            contagem = list(range(1, len(datas) + 1))
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=datas,
                y=contagem,
                mode='lines+markers',
                name='Análises'
            ))
            
            fig.update_layout(
                title='Evolução do Número de Análises',
                xaxis_title='Data',
                yaxis_title='Número de Análises',
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Tags Mais Utilizadas
    st.subheader("🏷️ Tags Mais Utilizadas")
    if historico_analises:
        # Contar frequência de tags
        tags_frequencia = {}
        for analise in historico_analises:
            for tag in analise.get('tags', []):
                tags_frequencia[tag] = tags_frequencia.get(tag, 0) + 1
        
        if tags_frequencia:
            # Criar gráfico de barras horizontais
            fig = px.bar(
                x=list(tags_frequencia.values()),
                y=list(tags_frequencia.keys()),
                orientation='h',
                labels={'x': 'Frequência', 'y': 'Tag'},
                title='Frequência de Tags'
            )
            st.plotly_chart(fig, use_container_width=True)

# Adicionar após as configurações iniciais
def salvar_consumo_tokens(tokens_consumidos, tipo_operacao):
    try:
        # Adicionar usuário_id se disponível
        if 'username' in st.session_state:
            usuario_id = st.session_state.username
        else:
            usuario_id = None

        # Formatar dados para o Supabase
        payload = {
            "tipo": tipo_operacao,
            "total_tokens": tokens_consumidos,
            "plataforma": "copy" if tipo_operacao == "copy" else "analise",
            "tempo_processamento": 0, 
            "usuario_id": usuario_id,
            "data": datetime.now().isoformat()
        }

        # Salvar no Supabase
        response = supabase.table('metricas').insert(payload).execute()
        
        if response.data:
            return True
        else:
            st.error("Erro ao salvar consumo de tokens no Supabase.")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar consumo de tokens: {e}")
        return False

# Adicionar após as configurações iniciais
def salvar_metricas(metricas_data):
    """Salva as métricas de performance no Supabase"""
    try:
        # Adicionar usuário_id se disponível
        if 'username' in st.session_state:
            metricas_data['usuario_id'] = st.session_state.username

        # Formatar dados para o Supabase
        if "analise" in metricas_data:
            analise = metricas_data["analise"]
            payload = {
                "tipo": "analise",
                "plataforma": analise["plataforma"],
                "total_tokens": 0,
                "tempo_processamento": analise["tempo_processamento"],
                "data": datetime.now().isoformat()
            }
        elif "copy" in metricas_data:
            payload = {
                "tipo": "copy",
                "plataforma": "copy",
                "total_tokens": 0, 
                "tempo_processamento": 0,
                "data": datetime.now().isoformat()
            }
        elif "feedback" in metricas_data:
            feedback = metricas_data["feedback"]
            payload = {
                "tipo": "feedback",
                "plataforma": "feedback",
                "total_tokens": 0,
                "tempo_processamento": 0,
                "data": datetime.now().isoformat()
            }

        # Salvar no Supabase
        response = supabase.table('metricas').insert(payload).execute()
        
        if response.data:
            return True
        else:
            st.error("Erro ao salvar métricas no Supabase.")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar métricas: {e}")
        return False

# --- Interface Streamlit ---
st.set_page_config(page_title="Gerador de Copy Mencare", layout="wide")

# Verificar autenticação
if not st.session_state.autenticado:
    login()
else:
    # Inicializar st.session_state se não existir
    if 'generated_copy' not in st.session_state:
        st.session_state.generated_copy = ""
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    if 'historico' not in st.session_state:
        st.session_state.historico = []
    if 'analise_leads' not in st.session_state:
        st.session_state.analise_leads = None

    # Barra superior com informações do usuário e botão de logout
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("🤖 Gerador de Copy Mencare ✍️")
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.autenticado = False
            st.session_state.username = None
            st.session_state.login_success = False
            st.rerun()

    # Criar as abas
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Gerar Copy", "📚 Histórico", "📊 Análise de Leads", "📈 Métricas", "🎯 Dashboard"])

    with tab1:
        st.markdown("Preencha os campos abaixo para gerar sua copy e, opcionalmente, salvá-la no Baserow.")

        with st.sidebar:
            st.header("⚙️ Configurações da Copy")
            plataforma_opcoes = [
                "Disparo de WhatsApp",
                "Email Marketing",
                "Conteúdo para Redes Sociais (Feed)",
                "Conteúdo para Redes Sociais (Stories)",
                "Copy para SMS"
            ]
            plataforma = st.selectbox("Selecione a Plataforma:", plataforma_opcoes)
            
            # Mostrar limite de tokens para a plataforma selecionada
            tokens_limite = TOKENS_POR_PLATAFORMA.get(plataforma, 300)
            st.info(f"Limite de tokens para esta plataforma: {tokens_limite}")
            
            objetivo = st.text_input("🎯 Objetivo da Copy:", placeholder="Ex: Gerar leads, Vender produto X, Aumentar engajamento")
            publico_alvo = st.text_input("👥 Público-Alvo:", placeholder="Ex: Jovens de 18-25 anos interessados em tecnologia")
            produto_servico = st.text_input("🛍️ Produto/Serviço:", placeholder="Ex: Curso online de Python, Consultoria de Marketing Digital")
            tom_de_voz_opcoes = ["Formal", "Informal", "Amigável", "Persuasivo", "Divertido", "Urgente"]
            tom_de_voz = st.selectbox("🗣️ Tom de Voz:", tom_de_voz_opcoes)
            cta = st.text_input("📢 Call to Action (CTA):", placeholder="Ex: Compre agora, Saiba mais, Inscreva-se já")
            informacoes_adicionais = st.text_area("ℹ️ Informações Adicionais (Opcional):", placeholder="Ex: Mencionar promoção de 20% OFF, destacar benefício Y")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📝 Campos para Geração")
            if st.button("✨ Gerar Copy Agora!", type="primary", use_container_width=True):
                if not all([plataforma, objetivo, publico_alvo, produto_servico, tom_de_voz, cta]):
                    st.warning("Por favor, preencha todos os campos obrigatórios antes de gerar a copy.")
                else:
                    with st.spinner("Gerando sua copy com IA... Aguarde! 🧠"):
                        copy_gerada = gerar_copy_openai(
                            plataforma, objetivo, publico_alvo, produto_servico, tom_de_voz, cta, informacoes_adicionais
                        )
                        if copy_gerada:
                            st.session_state.generated_copy = copy_gerada
                            st.session_state.form_data = {
                                "plataforma": plataforma,
                                "objetivo": objetivo,
                                "publico_alvo": publico_alvo,
                                "produto_servico": produto_servico,
                                "tom_de_voz": tom_de_voz,
                                "cta": cta,
                                "copy_gerada": copy_gerada,
                                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            }
                            # Adicionar ao histórico
                            st.session_state.historico.append(st.session_state.form_data)
                        else:
                            st.session_state.generated_copy = ""
                            st.session_state.form_data = {}

        with col2:
            st.subheader("📄 Copy Gerada")
            if st.session_state.generated_copy:
                st.text_area("Resultado:", st.session_state.generated_copy, height=300)
                if SUPABASE_URL and SUPABASE_KEY:
                    if st.button("💾 Salvar Copy no Supabase", use_container_width=True):
                        with st.spinner("Salvando no Supabase..."):
                            if st.session_state.form_data:
                                salvar_no_supabase(st.session_state.form_data)
                            else:
                                st.error("Nenhuma copy gerada para salvar.")
                elif st.session_state.generated_copy:
                    st.info("Configure as variáveis de ambiente do Supabase para habilitar o salvamento.")
            else:
                st.info("A copy gerada aparecerá aqui.")

    with tab2:
        st.subheader("📚 Histórico de Copies")
        
        if not st.session_state.historico:
            st.info("Nenhuma copy gerada ainda. O histórico aparecerá aqui após gerar algumas copies.")
        else:
            # Mostrar histórico em ordem reversa (mais recente primeiro)
            for idx, item in enumerate(reversed(st.session_state.historico)):
                with st.expander(f"Copy #{len(st.session_state.historico) - idx} - {item['plataforma']} - {item['data_geracao']}"):
                    st.write(f"**Plataforma:** {item['plataforma']}")
                    st.write(f"**Objetivo:** {item['objetivo']}")
                    st.write(f"**Público-Alvo:** {item['publico_alvo']}")
                    st.write(f"**Produto/Serviço:** {item['produto_servico']}")
                    st.write(f"**Tom de Voz:** {item['tom_de_voz']}")
                    st.write(f"**CTA:** {item['cta']}")
                    st.write("**Copy Gerada:**")
                    st.text_area("", item['copy_gerada'], height=200, key=f"copy_{idx}")
                    
                    # Botão para copiar a copy
                    if st.button("📋 Copiar Copy", key=f"copy_btn_{idx}"):
                        st.code(item['copy_gerada'])
                        st.success("Copy copiada para a área de transferência!")

    with tab3:
        st.subheader("📊 Análise de Leads via CSV")
        
        # Configurações da análise
        col1, col2 = st.columns(2)
        
        with col1:
            plataforma_analise = st.selectbox(
                "Selecione a Plataforma para Análise:",
                ["Disparo de WhatsApp", "Email Marketing", "Conteúdo para Redes Sociais (Feed)", 
                 "Conteúdo para Redes Sociais (Stories)", "Copy para SMS"],
                key="plataforma_analise"
            )
        
        with col2:
            objetivo_analise = st.text_input(
                "Objetivo da Análise:",
                placeholder="Ex: Aumentar conversões, Melhorar engajamento, Gerar vendas",
                key="objetivo_analise"
            )
        
        # Upload de múltiplos arquivos CSV
        uploaded_files = st.file_uploader(
            "Escolha um ou mais arquivos CSV com seus leads", 
            type=['csv'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            try:
                # Lista para armazenar todos os DataFrames
                dfs = []
                total_leads = 0
                
                # Processar cada arquivo
                for uploaded_file in uploaded_files:
                    df = pd.read_csv(uploaded_file)
                    dfs.append(df)
                    total_leads += len(df)
                
                # Mostrar preview dos dados
                st.subheader("📋 Preview dos Dados")
                
                # Criar abas para cada arquivo
                tabs = st.tabs([f"Arquivo {i+1}" for i in range(len(dfs))])
                
                for i, tab in enumerate(tabs):
                    with tab:
                        st.write(f"**Arquivo {i+1}:** {uploaded_files[i].name}")
                        st.write(f"Total de leads neste arquivo: {len(dfs[i])}")
                        st.dataframe(dfs[i].head())
                        st.write("Colunas disponíveis:")
                        for col in dfs[i].columns:
                            st.write(f"- {col}")
                
                # Mostrar informações básicas do dataset combinado
                st.subheader("ℹ️ Informações do Dataset Combinado")
                st.write(f"Total de leads em todos os arquivos: {total_leads}")
                
                # Botão para iniciar análise
                if st.button("🔍 Iniciar Análise", type="primary"):
                    if not objetivo_analise:
                        st.warning("Por favor, defina um objetivo para a análise.")
                    else:
                        with st.spinner("Analisando seus leads... Isso pode levar alguns minutos."):
                            # Combinar todos os DataFrames
                            df_combinado = pd.concat(dfs, ignore_index=True)
                            
                            # Remover duplicatas se houver
                            df_combinado = df_combinado.drop_duplicates()
                            
                            # Realizar a análise
                            analise, analise_id = analisar_leads_csv(df_combinado, plataforma_analise, objetivo_analise)
                            if analise:
                                st.session_state.analise_leads = analise
                                st.session_state.analise_id = analise_id
                                st.success("Análise concluída e salva no histórico!")
                
                # Mostrar resultados da análise
                if st.session_state.analise_leads:
                    st.subheader("📊 Resultados da Análise")
                    st.markdown(st.session_state.analise_leads)
                    
                    # Seção de feedback
                    st.subheader("💭 Feedback da Análise")
                    with st.form("feedback_form"):
                        pontos_positivos = st.text_area("Pontos Positivos:", 
                            placeholder="O que você achou mais útil nesta análise?")
                        pontos_melhorar = st.text_area("Pontos a Melhorar:", 
                            placeholder="O que poderia ser melhorado nesta análise?")
                        nota = st.slider("Nota da Análise:", 1, 5, 3)
                        feedback_submit = st.form_submit_button("Enviar Feedback")
                        
                        if feedback_submit:
                            feedback_data = {
                                "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                "pontos_positivos": pontos_positivos,
                                "pontos_melhorar": pontos_melhorar,
                                "nota": nota
                            }
                            if salvar_feedback(st.session_state.analise_id, feedback_data):
                                st.success("Feedback enviado com sucesso! Obrigado por ajudar a melhorar nossas análises.")
                    
                    # Botão para copiar a análise
                    if st.button("📋 Copiar Análise"):
                        st.code(st.session_state.analise_leads)
                        st.success("Análise copiada para a área de transferência!")
            
            except Exception as e:
                st.error(f"Erro ao processar os arquivos CSV: {e}")
                st.info("Certifique-se de que os arquivos estão no formato CSV válido e contêm dados estruturados.")
        else:
            st.info("Faça upload de um ou mais arquivos CSV para começar a análise.")

        mostrar_historico_analises()

    with tab4:
        st.subheader("📈 Métricas de Performance")
        
        metricas = carregar_metricas()
        
        if not metricas:
            st.info("Nenhuma métrica disponível ainda. Comece a usar o sistema para gerar métricas.")
        else:
            # Métricas gerais
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Análises", metricas["total_analises"])
                st.metric("Total de Copies", metricas["total_copies"])
            
            with col2:
                st.metric("Tempo Médio de Análise", f"{metricas['tempo_medio_analise']:.2f}s")
                st.metric("Média de Notas", f"{metricas['media_notas']:.1f} ⭐")
            
            with col3:
                st.metric("Total de Feedback", metricas["total_feedback"])
            
            # Gráficos e análises detalhadas
            st.subheader("📊 Análise Detalhada")
            
            # Plataformas mais usadas
            st.write("**Plataformas Mais Utilizadas**")
            plataformas_df = pd.DataFrame(
                list(metricas["plataformas_mais_usadas"].items()),
                columns=["Plataforma", "Quantidade"]
            )
            st.bar_chart(plataformas_df.set_index("Plataforma"))
            
            # Objetivos mais comuns
            st.write("**Objetivos Mais Comuns**")
            objetivos_df = pd.DataFrame(
                list(metricas["objetivos_mais_comuns"].items()),
                columns=["Objetivo", "Quantidade"]
            )
            st.bar_chart(objetivos_df.set_index("Objetivo"))
            
            # Últimas análises
            st.subheader("📋 Últimas Análises")
            if metricas["analises"]:
                ultimas_analises = pd.DataFrame(metricas["analises"][-5:])
                st.dataframe(ultimas_analises[["data", "plataforma", "objetivo", "total_leads", "tempo_processamento"]])
            
            # Exportar métricas
            if st.button("📥 Exportar Métricas"):
                metricas_json = json.dumps(metricas, indent=4)
                st.download_button(
                    label="Baixar Métricas",
                    data=metricas_json,
                    file_name=f"metricas_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )

    with tab5:
        gerar_dashboard()

    st.markdown("---")