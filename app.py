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

def verificar_credenciais(email, password):
    """Verifica se as credenciais do usuário são válidas usando Supabase Auth"""
    try:
        # O cliente Supabase já deve estar inicializado globalmente
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            return True
    except Exception as e:
        # Tratar erros específicos do Supabase se necessário, ex: usuário não encontrado, senha inválida
        st.error(f"Erro de autenticação: {e}")
        return False
    return False

def inicializar_autenticacao():
    """Inicializa o estado de autenticação"""
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    if 'username' not in st.session_state: # Manter 'username' para consistência interna, mas ele guardará o email
        st.session_state.username = None
    if 'login_success' not in st.session_state:
        st.session_state.login_success = False

def login():
    """Interface de login"""
    st.title("🔐 Login Mencare IA")
    
    # Se o login foi bem-sucedido, mostrar mensagem e redirecionar
    if st.session_state.login_success:
        st.success("Login realizado com sucesso!")
        st.session_state.login_success = False # Resetar para evitar loop
        st.session_state.autenticado = True
        st.rerun()
        return
    
    with st.form("login_form"):
        email = st.text_input("Email") # Alterado de Usuário para Email
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            if verificar_credenciais(email, password):
                st.session_state.username = email # Armazenar o email como 'username'
                st.session_state.login_success = True
                st.rerun()
            else:
                st.error("Email ou senha inválidos!")

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
        salvar_consumo_tokens(tokens_consumidos, "copy", st.session_state.username) # Passar username
        
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
        if 'username' in st.session_state and st.session_state.username:
            # Buscar o ID do usuário no Supabase com base no email (st.session_state.username)
            user_response = supabase.table('users').select('id').eq('email', st.session_state.username).execute()
            if user_response.data:
                data_to_save['usuario_id'] = user_response.data[0]['id']
            else:
                auth_user = supabase.auth.get_user()
                if auth_user and auth_user.user:
                    data_to_save['usuario_id'] = auth_user.user.id
                else:
                     st.warning("Não foi possível obter o ID do usuário autenticado para salvar a copy.")


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
    """Salva a análise de leads no Supabase e retorna o ID da análise salva."""
    try:
        auth_user = supabase.auth.get_user()
        current_user_id = None
        if auth_user and auth_user.user:
            current_user_id = auth_user.user.id
        else:
            st.error("Usuário não autenticado. Não é possível salvar a análise de leads.")
            return None # Retornar None em caso de falha na autenticação

        payload = {
            "plataforma": analise_data.get("plataforma"),
            "objetivo": analise_data.get("objetivo"),
            "total_leads": analise_data.get("total_leads"), 
            "colunas": json.dumps(analise_data.get("colunas", [])),
            "analise": analise_data.get("analise"),
            "tempo_processamento": analise_data.get("tempo_processamento"),
            "resumo_estatistico": json.dumps(analise_data.get("resumo_estatistico", {})),
            "usuario_id": current_user_id,
            "data": datetime.now().isoformat()
        }

        print(f"DEBUG: Tentando salvar em analises_leads com usuario_id: {current_user_id}")
        response = supabase.table('analises_leads').insert(payload).execute()
        
        if response.data and len(response.data) > 0:
            saved_analise_id = response.data[0]['id'] # UUID da análise salva
            if 'tags' in analise_data and analise_data['tags']:
                tags_para_salvar = []
                for tag_nome in analise_data['tags']:
                    categoria_tag = "Personalizada"
                    for cat, tags_list in TAGS_PREDEFINIDAS.items():
                        if tag_nome in tags_list:
                            categoria_tag = cat
                            break
                    tags_para_salvar.append({
                        "analise_id": saved_analise_id, # Usar o UUID aqui
                        "categoria": categoria_tag,
                        "tag": tag_nome,
                        "usuario_id": current_user_id 
                    })
                if tags_para_salvar:
                    tags_response = supabase.table('tags').insert(tags_para_salvar).execute()
                    if not (tags_response.data and len(tags_response.data) > 0):
                        st.warning("Análise salva, mas houve um erro ao salvar algumas ou todas as tags.")
            
            st.success("Análise e tags salvas com sucesso no Supabase!")
            return saved_analise_id # Retornar o UUID da análise salva
        else:
            error_msg = response.error.message if response.error else "Erro desconhecido"
            st.error(f"Erro ao salvar análise no Supabase: {error_msg}")
            return None # Retornar None em caso de falha
    except Exception as e:
        st.error(f"Erro excepcional ao salvar análise: {e}")
        return None # Retornar None em caso de exceção

def atualizar_tags_analise(analise_id, novas_tags):
    """Atualiza as tags de uma análise específica no Supabase."""
    try:
        auth_user = supabase.auth.get_user()
        if not (auth_user and auth_user.user):
            st.error("Usuário não autenticado. Não é possível atualizar as tags.")
            return False
        user_id = auth_user.user.id

        # 1. Deletar tags antigas para esta analise_id e usuario_id (para segurança)
        delete_response = supabase.table('tags').delete().match({'analise_id': analise_id, 'usuario_id': user_id}).execute()

        # 2. Inserir novas tags
        if novas_tags:
            tags_para_inserir = []
            for tag_nome in novas_tags:
                # Determinar a categoria da tag. Por enquanto, vou usar "Personalizada"
                categoria_tag = "Personalizada" # Default
                for cat, tags_list in TAGS_PREDEFINIDAS.items():
                    if tag_nome in tags_list:
                        categoria_tag = cat
                        break
                
                tags_para_inserir.append({
                    'analise_id': analise_id,
                    'categoria': categoria_tag, # Adicionar categoria da tag
                    'tag': tag_nome,
                    'usuario_id': user_id
                })
            
            if tags_para_inserir:
                insert_response = supabase.table('tags').insert(tags_para_inserir).execute()
                if insert_response.data:
                    return True
                else:
                    st.error(f"Erro ao inserir novas tags no Supabase: {insert_response.error.message if insert_response.error else 'Erro desconhecido'}")
                    return False
        return True # Verdadeiro se não havia novas tags para inserir (tags antigas foram removidas)

    except Exception as e:
        st.error(f"Erro ao atualizar tags no Supabase: {e}")
        return False

def gerar_insights_com_tags(analise_atual, tags_da_analise_atual):
    """Gera insights baseados nas tags da análise, buscando no Supabase."""
    try:
        auth_user = supabase.auth.get_user()
        if not (auth_user and auth_user.user):
            st.info("Usuário não autenticado. Insights baseados em tags não podem ser gerados.")
            return "Nenhum insight similar encontrado (usuário não autenticado)."
        user_id = auth_user.user.id
        analise_id_atual = analise_atual['id']

        if not tags_da_analise_atual:
            return "Nenhuma tag fornecida para buscar insights similares."

        # 1. Encontrar todas as analise_ids (diferentes da atual) que compartilham pelo menos uma tag com a análise atual
        analises_similares_ids = set()
        for tag_nome in tags_da_analise_atual:
            response_tags_similares = supabase.table('tags')\
                .select('analise_id')\
                .eq('usuario_id', user_id)\
                .eq('tag', tag_nome)\
                .neq('analise_id', analise_id_atual)\
                .execute()
            if response_tags_similares.data:
                for item in response_tags_similares.data:
                    analises_similares_ids.add(item['analise_id'])
        
        if not analises_similares_ids:
            return "Nenhum insight similar encontrado com as tags fornecidas."

        # 2. Buscar os detalhes dessas análises similares
        response_analises_similares = supabase.table('analises_leads')\
            .select('id, data, plataforma, objetivo, analise')\
            .in_('id', list(analises_similares_ids))\
            .order('data', desc=True)\
            .limit(5) .execute() # Limitar o número de análises similares para não sobrecarregar

        insights_gerados = []
        if response_analises_similares.data:
            insights_gerados.append("\n### Insights de Análises Anteriores com Tags Similares:")
            for analise_similar_db in response_analises_similares.data:
                data_iso = analise_similar_db.get('data')
                data_formatada = str(data_iso)
                if data_iso:
                    try:
                        dt_obj = datetime.fromisoformat(data_iso.replace('Z', '+00:00').replace('+0000', '+00:00'))
                        data_formatada = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                    except ValueError:
                        try:
                            dt_obj = datetime.strptime(data_iso, "%d/%m/%Y %H:%M:%S")
                            data_formatada = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                        except ValueError:
                            pass
                
                insights_gerados.append(f"""
**Data:** {data_formatada}
**Plataforma:** {analise_similar_db.get('plataforma', 'N/A')}
**Objetivo:** {analise_similar_db.get('objetivo', 'N/A')}
**Análise Resumida:** {analise_similar_db.get('analise', 'N/A')[:200] + '...' if analise_similar_db.get('analise') else 'N/A'}
---""")
            return "\n".join(insights_gerados)
        else:
            return "Nenhum insight similar encontrado com as tags fornecidas."

    except Exception as e:
        st.error(f"Erro ao gerar insights com tags do Supabase: {e}")
        return "Erro ao gerar insights."

def carregar_historico_analises():
    """Carrega o histórico de análises do usuário atual a partir do Supabase."""
    try:
        auth_user = supabase.auth.get_user()
        if not (auth_user and auth_user.user):
            st.error("Usuário não autenticado. Não é possível carregar o histórico de análises.")
            return []

        user_id = auth_user.user.id
        
        # Buscar análises do usuário
        response_analises = supabase.table('analises_leads').select('*').eq('usuario_id', user_id).order('data', desc=True).execute()
        
        if response_analises.data:
            historico_com_tags = []
            for analise_db in response_analises.data:
                # Para cada análise, buscar suas tags
                response_tags = supabase.table('tags').select('tag').eq('analise_id', analise_db['id']).execute()
                
                tags_da_analise = []
                if response_tags.data:
                    tags_da_analise = [item['tag'] for item in response_tags.data]
                
                # Montar o dicionário da análise no formato esperado
                # Convertendo campos JSON de string para dict/list se necessário
                colunas = json.loads(analise_db.get('colunas', '[]')) if isinstance(analise_db.get('colunas'), str) else analise_db.get('colunas', [])
                resumo_estatistico = json.loads(analise_db.get('resumo_estatistico', '{}')) if isinstance(analise_db.get('resumo_estatistico'), str) else analise_db.get('resumo_estatistico', {})

                analise_formatada = {
                    "id": analise_db['id'],
                    "data": analise_db.get('data_criacao') or analise_db.get('data', datetime.now().strftime("%d/%m/%Y %H:%M:%S")), # Ajustar nome da coluna de data se necessário
                    "plataforma": analise_db['plataforma'],
                    "objetivo": analise_db['objetivo'],
                    "total_leads": analise_db.get('total_leads'),
                    "colunas": colunas,
                    "analise": analise_db['analise'],
                    "tempo_processamento": analise_db.get('tempo_processamento'),
                    "resumo_estatistico": resumo_estatistico,
                    "tags": tags_da_analise,
                    "usuario_id": analise_db.get('usuario_id')
                }
                historico_com_tags.append(analise_formatada)
            return historico_com_tags
        else:
            return []
            
    except Exception as e:
        st.error(f"Erro ao carregar histórico de análises do Supabase: {e}")
        return []

def salvar_feedback(analise_id, feedback_data):
    """Salva o feedback no Supabase"""
    try:
        auth_user = supabase.auth.get_user()
        if not (auth_user and auth_user.user):
            st.error("Usuário não autenticado. Não é possível salvar o feedback.")
            return False
        
        current_user_id = auth_user.user.id

        # Formatar dados para o Supabase
        payload = {
            "analise_id": analise_id,
            "data": datetime.now().isoformat(), # Adicionando data do feedback
            "pontos_positivos": feedback_data.get("pontos_positivos"),
            "pontos_melhorar": feedback_data.get("pontos_melhorar"),
            "nota": feedback_data.get("nota"),
            "editado": False, 
            "ultima_edicao": datetime.now().isoformat(), # Definindo na criação também
            "historico_edicoes": json.dumps([]),
            "usuario_id": current_user_id 
        }

        # Salvar no Supabase
        response = supabase.table('feedback').insert(payload).execute()
        
        if response.data:
            return True
        else:
            st.error(f"Erro ao salvar feedback: {response.error.message if response.error else 'Erro desconhecido'}")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar feedback: {e}")
        return False

def editar_feedback(analise_id, novo_feedback_data):
    """Edita um feedback existente no Supabase."""
    try:
        auth_user = supabase.auth.get_user()
        if not (auth_user and auth_user.user):
            st.error("Usuário não autenticado. Não é possível editar o feedback.")
            return False
        user_id = auth_user.user.id

        # 1. Buscar o feedback existente do usuário para esta análise
        # É importante buscar pelo user_id para garantir que o usuário só edite seu próprio feedback.
        response_get = supabase.table('feedback')\
            .select('*')\
            .eq('analise_id', analise_id)\
            .eq('usuario_id', user_id)\
            .order('created_at', desc=True)\
            .limit(1)\
            .maybe_single()\
            .execute()

        # Adicionar verificação para a própria `response`
        if response_get is None:
            st.warning("A consulta ao Supabase para carregar feedback retornou None inesperadamente.")
            return None

        # Se .maybe_single() não encontrar nada, response.data será None.
        # A exceção está sendo pega no bloco `except` abaixo.

        if not response_get.data:
            st.error("Feedback original não encontrado para editar ou você não tem permissão.")
            return False
        
        feedback_atual = response_get.data
        feedback_id_db = feedback_atual['id'] # ID do registro de feedback no banco

        # 2. Preparar o histórico
        historico_edicoes_atual_str = feedback_atual.get('historico_edicoes', '[]')
        historico_edicoes_atual = []
        if isinstance(historico_edicoes_atual_str, str):
            try:
                historico_edicoes_atual = json.loads(historico_edicoes_atual_str)
            except json.JSONDecodeError:
                st.warning("Histórico de edições do feedback está mal formatado.")
        elif isinstance(historico_edicoes_atual_str, list):
            historico_edicoes_atual = historico_edicoes_atual_str
        
        feedback_anterior_para_historico = {
            "pontos_positivos": feedback_atual.get('pontos_positivos'),
            "pontos_melhorar": feedback_atual.get('pontos_melhorar'),
            "nota": feedback_atual.get('nota'),
            "ultima_edicao_original": feedback_atual.get('ultima_edicao') or feedback_atual.get('updated_at'), # Usar updated_at como fallback
            "timestamp_arquivamento": datetime.now().isoformat()
        }
        historico_edicoes_atual.append(feedback_anterior_para_historico)

        # 3. Preparar dados para atualização
        dados_para_atualizar = {
            "pontos_positivos": novo_feedback_data.get("pontos_positivos"),
            "pontos_melhorar": novo_feedback_data.get("pontos_melhorar"),
            "nota": novo_feedback_data.get("nota"),
            "editado": True,
            "ultima_edicao": datetime.now().isoformat(),
            "historico_edicoes": json.dumps(historico_edicoes_atual) # Salvar como string JSON
        }

        # 4. Atualizar o feedback no Supabase usando o ID do registro de feedback
        response_update = supabase.table('feedback').update(dados_para_atualizar).eq('id', feedback_id_db).execute()

        if response_update.data:
            return True
        else:
            error_msg = response_update.error.message if response_update.error else "Erro desconhecido"
            st.error(f"Erro ao atualizar feedback no Supabase: {error_msg}")
            return False

    except Exception as e:
        st.error(f"Erro excepcional ao editar feedback: {e}")
        return False

def salvar_metricas_plataforma(plataforma, metricas_data):
    """Salva métricas específicas da plataforma no Supabase"""
    try:
        auth_user = supabase.auth.get_user()
        
        if not (auth_user and auth_user.user):
            st.error("Usuário não autenticado. Não é possível salvar métricas da plataforma.")
            return False
        
        current_user_id = auth_user.user.id # Definir claramente a variável com o ID

        # Formatar dados para o Supabase
        payload = {
            "plataforma": plataforma,
            "metricas": json.dumps(metricas_data), 
            "data": datetime.now().isoformat(),
            "usuario_id": current_user_id 
        }
        
        # Log para depuração
        print(f"DEBUG: Tentando salvar em metricas_plataforma com usuario_id: {current_user_id}, tipo: {type(current_user_id)}")

        # Salvar no Supabase
        response = supabase.table('metricas_plataforma').insert(payload).execute()
        
        if response.data:
            return True
        else:
            st.error(f"Erro ao salvar métricas no Supabase: {response.error.message if response.error else 'Erro desconhecido'}")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar métricas da plataforma: {e}")
        return False

def analisar_leads_csv_openai(df, plataforma, objetivo, tempo_inicio_global, resumo_estatistico_global):
    progress_bar = st.progress(0)
    status_text = st.empty()
    try:
        status_text.text("🔄 Preparando dados para análise (OpenAI)... ")
        progress_bar.progress(10)
        
        colunas_relevantes = df.columns[:9]
        df_otimizado = df[colunas_relevantes].copy()
        max_linhas = 100
        if len(df_otimizado) > max_linhas:
            df_otimizado = df_otimizado.sample(n=max_linhas, random_state=42)
        df_str = df_otimizado.to_string()

        feedbacks_contexto = []
        try:
            auth_user = supabase.auth.get_user()
            if auth_user and auth_user.user:
                user_id = auth_user.user.id
                response_feedbacks = supabase.table('feedback')\
                    .select('pontos_positivos, pontos_melhorar')\
                    .eq('usuario_id', user_id)\
                    .order('created_at', desc=True)\
                    .limit(10).execute()
                if response_feedbacks and response_feedbacks.data:
                    for fb_item in response_feedbacks.data:
                        if fb_item.get('pontos_positivos') or fb_item.get('pontos_melhorar'):
                            feedbacks_contexto.append(fb_item)
                            if len(feedbacks_contexto) >= 3:
                                break
        except Exception as e_fb:
            st.warning(f"Não foi possível carregar feedbacks para contexto OpenAI: {e_fb}")

        contexto_aprendizado = ""
        if feedbacks_contexto:
            contexto_aprendizado = """\
Baseado em feedbacks anteriores dos usuários, considere:"""
            for feedback_item in feedbacks_contexto:
                if feedback_item.get('pontos_positivos'):
                    contexto_aprendizado += f"\
- Pontos positivos anteriores: {feedback_item['pontos_positivos']}"
                if feedback_item.get('pontos_melhorar'):
                    contexto_aprendizado += f"\
- Pontos a melhorar: {feedback_item['pontos_melhorar']}"

        status_text.text("⚙️ Configurando análise com IA...")
        progress_bar.progress(50)
        prompt = f'''
        Você é um especialista em análise de dados e marketing digital.
        Analise os seguintes dados de leads e forneça insights relevantes para {plataforma} com o objetivo de {objetivo}.
        {contexto_aprendizado}
        Resumo dos dados:
        - Total de leads: {resumo_estatistico_global['total_leads']}
        - Amostra analisada: {resumo_estatistico_global['amostra_analisada']}
        - Colunas analisadas: {', '.join(resumo_estatistico_global['colunas_analisadas'])}
        Estatísticas básicas:
        {json.dumps(resumo_estatistico_global['estatisticas'], indent=2)}
        Dados da amostra:
        {df_str}
        Por favor, forneça:
        1. Análise geral dos dados
        2. Insights específicos para {plataforma}
        3. Recomendações de estratégia para atingir o objetivo de {objetivo}
        4. Sugestões de segmentação dos leads
        5. Possíveis abordagens personalizadas
        Mantenha a análise clara e objetiva, focando em insights acionáveis.
        '''
        status_text.text("🤖 Gerando análise com IA (OpenAI)... ")
        progress_bar.progress(70)
        response_openai = client.chat.completions.create(
            model="gpt-4.1-mini", 
            messages=[{"role": "system", "content": "Você é um especialista em análise de dados e marketing digital."}, 
                      {"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=800)
        
        tokens_consumidos = response_openai.usage.total_tokens
        username_para_tokens = st.session_state.get('username') # Usar .get() para segurança
        salvar_consumo_tokens(tokens_consumidos, "analise", username_para_tokens)
        
        status_text.text("✨ Finalizando e formatando análise (OpenAI)... ")
        progress_bar.progress(90)
        analise_texto_ia = response_openai.choices[0].message.content.strip()
        tempo_processamento_ia = time.time() - tempo_inicio_global
        
        status_text.text("✅ Análise (OpenAI) concluída!")
        progress_bar.progress(100)
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        return analise_texto_ia, tempo_processamento_ia

    except Exception as e_openai:
        status_text.text(f"❌ Erro na análise com OpenAI: {e_openai}")
        progress_bar.progress(0)
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        st.error(f"Erro ao analisar os leads com OpenAI: {e_openai}")
        return None, 0

def analisar_leads_csv(df, plataforma, objetivo):
    """
    Prepara dados, chama a análise da OpenAI, salva os resultados e retorna a análise, ID e tempo de processamento.
    """
    # Definir tempo_inicio aqui, fora do try, para garantir que sempre exista se a função for chamada.
    # No entanto, para medir o tempo do bloco 'try', ele deve estar dentro.
    # Garantir que seja a primeira coisa no try.
    try:
        tempo_inicio = time.time() # Primeira linha DENTRO do try para medir a duração correta.
        
        colunas_relevantes = df.columns[:9]
        df_otimizado_para_stats = df[colunas_relevantes].copy()
        max_linhas_stats = 100 
        if len(df_otimizado_para_stats) > max_linhas_stats:
            df_otimizado_para_stats = df_otimizado_para_stats.sample(n=max_linhas_stats, random_state=42)

        resumo_estatistico = {
            "total_leads": len(df),
            "colunas_analisadas": list(colunas_relevantes),
            "amostra_analisada": len(df_otimizado_para_stats),
            "estatisticas": {}
        }
        for coluna in colunas_relevantes:
            if df_otimizado_para_stats[coluna].dtype in ['int64', 'float64']:
                resumo_estatistico["estatisticas"][coluna] = {
                    "media": df_otimizado_para_stats[coluna].mean(),
                    "mediana": df_otimizado_para_stats[coluna].median(),
                    "min": df_otimizado_para_stats[coluna].min(),
                    "max": df_otimizado_para_stats[coluna].max()
                }
            else:
                resumo_estatistico["estatisticas"][coluna] = {
                    "valores_mais_frequentes": df_otimizado_para_stats[coluna].value_counts().head().to_dict()
                }

        analise_gerada_pela_ia, tempo_processamento_openai = analisar_leads_csv_openai(
            df, plataforma, objetivo, tempo_inicio, resumo_estatistico # tempo_inicio é passado aqui
        )

        if analise_gerada_pela_ia:
            analise_payload_para_salvar = {
                "plataforma": plataforma,
                "objetivo": objetivo,
                "total_leads": len(df), 
                "colunas": list(df.columns), 
                "analise": analise_gerada_pela_ia,
                "tempo_processamento": tempo_processamento_openai, # Este é o tempo da IA
                "resumo_estatistico": resumo_estatistico,
                "tags": [] 
            }
            
            db_analise_id_uuid = salvar_analise_leads(analise_payload_para_salvar)
            
            if db_analise_id_uuid:
                # Retornar o texto da análise, o ID do banco de dados e o tempo de processamento da IA
                return analise_gerada_pela_ia, db_analise_id_uuid, tempo_processamento_openai
            else:
                st.error("Falha ao salvar a análise no banco de dados (depois da IA).")
                return None, None, None # Falha ao salvar no DB
        else:
            # Se analise_gerada_pela_ia for None (erro na OpenAI)
            return None, None, None # Erro na OpenAI

    except Exception as e:
        # Se o NameError for aqui, significa que 'tempo_inicio' não foi definido antes de ser usado
        # na chamada de analisar_leads_csv_openai.
        st.error(f"Erro geral ao processar CSV e analisar leads: {e}")
        return None, None, None

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
        
        # Modificado para iterar diretamente e ajustar a numeração
        for idx, analise in enumerate(historico_analises):
            # Modificado para exibir Análise #idx+1
            with st.expander(f"Análise #{idx + 1} - {analise['plataforma']} - {analise['data']}"):
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
                feedback = carregar_feedback(analise['id'], analise.get('usuario_id')) # Passar usuario_id
                
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

def carregar_feedback(analise_id, usuario_id_analise):
    """Carrega o feedback para uma análise específica do Supabase."""
    try:
        auth_user = supabase.auth.get_user()
        user_id_logado = auth_user.user.id if auth_user and auth_user.user else None

        if not user_id_logado:
            st.info("Usuário não autenticado. Não é possível carregar o feedback.")
            return None

        response = supabase.table('feedback')\
            .select('*')\
            .eq('analise_id', analise_id)\
            .eq('usuario_id', user_id_logado)\
            .order('created_at', desc=True)\
            .limit(1)\
            .maybe_single()\
            .execute()

        # Adicionar verificação para a própria `response`
        if response is None:
            st.warning("A consulta ao Supabase para carregar feedback retornou None inesperadamente.")
            return None

        # Se .maybe_single() não encontrar nada, response.data será None.
        # A exceção está sendo pega no bloco `except` abaixo.

        if response.data is None:
            return None 

        feedback_db = response.data
        
        historico_edicoes_str = feedback_db.get('historico_edicoes')
        historico_edicoes = []
        if isinstance(historico_edicoes_str, str) and historico_edicoes_str:
            try:
                historico_edicoes = json.loads(historico_edicoes_str)
            except json.JSONDecodeError:
                st.warning(f"Falha ao decodificar historico_edicoes para feedback da analise_id {analise_id}")
        elif isinstance(historico_edicoes_str, list):
             historico_edicoes = historico_edicoes_str

        return {
            "id": feedback_db.get('id'),
            "analise_id": feedback_db.get('analise_id'),
            "pontos_positivos": feedback_db.get('pontos_positivos'),
            "pontos_melhorar": feedback_db.get('pontos_melhorar'),
            "nota": feedback_db.get('nota'),
            "editado": feedback_db.get('editado', False),
            "ultima_edicao": feedback_db.get('ultima_edicao') or feedback_db.get('updated_at'), # Usar updated_at como fallback
            "historico_edicoes": historico_edicoes,
            "usuario_id": feedback_db.get('usuario_id')
        }

    except Exception as e:
        # Converter a exceção para string para verificar se é o erro "204 No Content"
        error_str = str(e)
        # O erro reportado é: "{'message': 'Missing response', 'code': '204', ...}"
        # Verificar pela presença de 'code': '204' na string da exceção.
        if "'code': '204'" in error_str or "PGRST116" in error_str: # PGRST116 é o código PostgREST para "item não encontrado"
            # Este é o caso em que nenhum feedback foi encontrado (HTTP 204 ou erro semântico PGRST116).
            # Não é um erro fatal para a aplicação, apenas significa que não há dados.
            return None
        else:
            # Se for qualquer outro erro, mostrar a mensagem de erro.
            st.error(f"Erro ao carregar feedback do Supabase: {e}")
            return None

def carregar_metricas():
    """Carrega e calcula as métricas de performance do usuário a partir do Supabase."""
    try:
        auth_user = supabase.auth.get_user()
        if not (auth_user and auth_user.user):
            st.info("Usuário não autenticado. Métricas gerais não podem ser carregadas.")
            return {
                "total_analises": 0, "total_copies": 0, "tempo_medio_analise": 0.0,
                "media_notas": 0.0, "total_feedback": 0, "plataformas_mais_usadas": {},
                "objetivos_mais_comuns": {},
                "analises": []
            }
        user_id = auth_user.user.id

        metricas_calculadas = {
            "total_analises": 0,
            "total_copies": 0,
            "tempo_medio_analise": 0.0,
            "media_notas": 0.0,
            "total_feedback": 0,
            "plataformas_mais_usadas": defaultdict(int),
            "objetivos_mais_comuns": defaultdict(int),
            "analises": []
        }

        # 1. Total de Análises
        response_total_analises = supabase.table('analises_leads').select('id', count='exact').eq('usuario_id', user_id).execute()
        if response_total_analises.count is not None:
            metricas_calculadas["total_analises"] = response_total_analises.count

        # 2. Total de Copies
        response_total_copies = supabase.table('copies').select('id', count='exact').eq('usuario_id', user_id).execute()
        if response_total_copies.count is not None:
            metricas_calculadas["total_copies"] = response_total_copies.count

        # 3. Tempo Médio de Análise
        response_tempos_analise = supabase.table('metricas')\
            .select('tempo_processamento')\
            .eq('usuario_id', user_id)\
            .eq('tipo', 'analise')\
            .gt('tempo_processamento', 0)\
            .execute()
        if response_tempos_analise.data:
            tempos = [item['tempo_processamento'] for item in response_tempos_analise.data if item.get('tempo_processamento') is not None]
            if tempos:
                metricas_calculadas["tempo_medio_analise"] = sum(tempos) / len(tempos)

        # 4. Média de Notas e 5. Total de Feedback
        response_feedbacks = supabase.table('feedback')\
            .select('nota')\
            .eq('usuario_id', user_id)\
            .execute()
        if response_feedbacks.data:
            notas = [item['nota'] for item in response_feedbacks.data if item.get('nota') is not None]
            metricas_calculadas["total_feedback"] = len(response_feedbacks.data)
            if notas:
                metricas_calculadas["media_notas"] = sum(notas) / len(notas)
        
        # 6. Plataformas Mais Usadas, 7. Objetivos Mais Comuns, 8. Últimas Análises
        response_analises_detalhes = supabase.table('analises_leads')\
            .select('plataforma, objetivo, data, total_leads, tempo_processamento')\
            .eq('usuario_id', user_id)\
            .order('data', desc=True)\
            .limit(100) .execute() # Limitar para performance, dashboard mostra só top 5 anyway

        if response_analises_detalhes.data:
            for i, analise_item in enumerate(response_analises_detalhes.data):
                plataforma = analise_item.get('plataforma')
                objetivo = analise_item.get('objetivo')
                if plataforma:
                    metricas_calculadas["plataformas_mais_usadas"][plataforma] += 1
                if objetivo:
                    metricas_calculadas["objetivos_mais_comuns"][objetivo] += 1
                
                if i < 5: # Para a lista das 5 últimas análises
                    data_iso = analise_item.get('data') 
                    data_formatada = str(data_iso) # Default para string original
                    if data_iso:
                        try:
                            if isinstance(data_iso, str):
                                dt_obj = datetime.fromisoformat(data_iso.replace('Z', '+00:00').replace('+0000', '+00:00'))
                                data_formatada = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                            elif isinstance(data_iso, datetime):
                                data_formatada = data_iso.strftime("%d/%m/%Y %H:%M:%S")
                        except ValueError: # Tentar outro formato se ISO falhar
                            try:
                                if isinstance(data_iso, str):
                                    dt_obj = datetime.strptime(data_iso, "%d/%m/%Y %H:%M:%S")
                                    data_formatada = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                            except ValueError:
                                pass # Mantém str(data_iso)
                    
                    metricas_calculadas["analises"].append({
                        "data": data_formatada,
                        "plataforma": plataforma,
                        "objetivo": objetivo,
                        "total_leads": analise_item.get('total_leads'),
                        "tempo_processamento": analise_item.get('tempo_processamento')
                    })
            
        # Converter defaultdicts para dicts para o output final
        metricas_calculadas["plataformas_mais_usadas"] = dict(metricas_calculadas["plataformas_mais_usadas"])
        metricas_calculadas["objetivos_mais_comuns"] = dict(metricas_calculadas["objetivos_mais_comuns"])

        return metricas_calculadas

    except Exception as e:
        st.error(f"Erro ao carregar métricas gerais do Supabase: {e}")
        return {
            "total_analises": 0, "total_copies": 0, "tempo_medio_analise": 0.0,
            "media_notas": 0.0, "total_feedback": 0, "plataformas_mais_usadas": {},
            "objetivos_mais_comuns": {},
            "analises": []
        }

def gerar_dashboard():
    """Gera o dashboard com métricas e visualizações importantes"""
    st.subheader("📊 Dashboard Geral")
    
    # Carregar dados
    metricas = carregar_metricas()
    metricas_plataforma = carregar_metricas_plataforma()
    historico_analises = carregar_historico_analises()
    consumo_tokens = carregar_consumo_tokens()
    
    if not metricas and not metricas_plataforma and not historico_analises and not (consumo_tokens and consumo_tokens['total_tokens'] > 0):
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
                    consumo_tokens['por_operacao'].get('copy', 0),
                    consumo_tokens['por_operacao'].get('analise', 0),
                    consumo_tokens['por_operacao'].get('outro', 0) # Adicionar 'outro' se houver
                ],
                names=['Copy', 'Análise', 'Outro'],
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
def salvar_consumo_tokens(tokens_consumidos, tipo_operacao, username_email=None):
    try:
        usuario_id_supabase = None
        if username_email: # username_email é o email do usuário logado
            auth_user = supabase.auth.get_user() # Tenta obter o usuário da sessão Supabase
            if auth_user and auth_user.user:
                usuario_id_supabase = auth_user.user.id
            else:
                # Fallback se não conseguir o user da sessão auth (pode acontecer se o token expirou)
                # Tenta buscar pelo email, assumindo que st.session_state.username contém o email
                if 'username' in st.session_state and st.session_state.username:
                     user_lookup = supabase.table('users').select('id').eq('email', st.session_state.username).execute()
                     if user_lookup.data:
                         usuario_id_supabase = user_lookup.data[0]['id']

        if not usuario_id_supabase and 'username' in st.session_state and st.session_state.username:
             st.warning(f"Não foi possível determinar o ID do usuário Supabase para {st.session_state.username} ao salvar consumo de tokens. Tentando com o email como ID.")

        # Formatar dados para o Supabase
        payload = {
            "tipo": tipo_operacao,
            "total_tokens": tokens_consumidos,
            "plataforma": "copy" if tipo_operacao == "copy" else "analise",
            "tempo_processamento": 0, 
            "usuario_id": usuario_id_supabase, # Pode ser None se não encontrado
            "data": datetime.now().isoformat()
        }

        # Salvar no Supabase
        response = supabase.table('metricas').insert(payload).execute()
        
        if response.data:
            return True
        else:
            st.error(f"Erro ao salvar consumo de tokens no Supabase: {response.error.message if response.error else 'Erro desconhecido'}")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar consumo de tokens: {e}")
        return False

# Adicionar após as configurações iniciais
def salvar_metricas(metricas_data):
    """Salva as métricas de performance no Supabase"""
    try:
        usuario_id_supabase = None
        if 'username' in st.session_state and st.session_state.username: # username é o email
            auth_user = supabase.auth.get_user()
            if auth_user and auth_user.user:
                usuario_id_supabase = auth_user.user.id
            # metricas_data['usuario_id'] não é usado diretamente aqui, mas pego de st.session_state

        payload = {
            "data": datetime.now().isoformat(),
            "usuario_id": usuario_id_supabase # Pode ser None
        }

        if "analise" in metricas_data:
            analise = metricas_data["analise"]
            payload.update({
                "tipo": "analise",
                "plataforma": analise["plataforma"],
                "total_tokens": 0, # Tokens de análise são salvos por salvar_consumo_tokens
                "tempo_processamento": analise["tempo_processamento"]
            })
        elif "copy" in metricas_data: # 'copy' não parece ser um tipo usado aqui atualmente
            payload.update({
                "tipo": "copy_gerada", # Mudar para tipo distinto se necessário
                "plataforma": "copy_geral", # Ajustar conforme necessidade
                "total_tokens": 0, 
                "tempo_processamento": 0
            })
        elif "feedback" in metricas_data:
            # feedback = metricas_data["feedback"] # Não usado diretamente
            payload.update({
                "tipo": "feedback_recebido", # Mudar para tipo distinto
                "plataforma": "feedback_sistema", # Ajustar
                "total_tokens": 0,
                "tempo_processamento": 0,
            })
        else:
            st.warning("Tipo de métrica desconhecido para salvar.")
            return False


        # Salvar no Supabase
        response = supabase.table('metricas').insert(payload).execute()
        
        if response.data:
            return True
        else:
            st.error(f"Erro ao salvar métricas no Supabase: {response.error.message if response.error else 'Erro desconhecido'}")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar métricas: {e}")
        return False

def carregar_metricas_plataforma():
    """Carrega as métricas específicas da plataforma mais recentes do Supabase."""
    try:
        auth_user = supabase.auth.get_user()
        if not (auth_user and auth_user.user):
            # st.error("Usuário não autenticado. Não é possível carregar métricas da plataforma.")
            return {} 
        user_id = auth_user.user.id

        # Buscar todas as métricas de plataforma para o usuário
        response = supabase.table('metricas_plataforma') \
            .select('plataforma, metricas, data') \
            .eq('usuario_id', user_id) \
            .order('data', desc=True) \
            .execute()

        metricas_recentes_por_plataforma = {}
        if response.data:
            for item in response.data:
                plataforma = item['plataforma']
                # Se ainda não temos a métrica mais recente para esta plataforma, adicionamos
                if plataforma not in metricas_recentes_por_plataforma:
                    metricas_db = item.get('metricas')
                    if isinstance(metricas_db, str):
                        try:
                            metricas_recentes_por_plataforma[plataforma] = json.loads(metricas_db)
                        except json.JSONDecodeError:
                            st.warning(f"Falha ao decodificar JSON de métricas para a plataforma {plataforma}")
                            metricas_recentes_por_plataforma[plataforma] = METRICAS_POR_PLATAFORMA.get(plataforma, {}) # Fallback para estrutura padrão
                    elif isinstance(metricas_db, dict):
                        metricas_recentes_por_plataforma[plataforma] = metricas_db
                    else:
                        metricas_recentes_por_plataforma[plataforma] = METRICAS_POR_PLATAFORMA.get(plataforma, {}) # Fallback
            return metricas_recentes_por_plataforma
        return {} # Retornar dict vazio se não houver dados, para consistência

    except Exception as e:
        st.error(f"Erro ao carregar métricas da plataforma do Supabase: {e}")
        return {} # Retornar dict vazio em caso de erro

def carregar_consumo_tokens():
    """Carrega o consumo de tokens do usuário a partir do Supabase."""
    try:
        auth_user = supabase.auth.get_user()
        if not (auth_user and auth_user.user):
            return {
                "total_tokens": 0,
                "historico": [],
                "por_operacao": {"copy": 0, "analise": 0, "outro": 0}
            }
        user_id = auth_user.user.id

        response = supabase.table('metricas')\
            .select('total_tokens, tipo, plataforma, data')\
            .eq('usuario_id', user_id)\
            .gt('total_tokens', 0) \
            .order('data', desc=True)\
            .execute()

        consumo = {
            "total_tokens": 0,
            "historico": [],
            "por_operacao": defaultdict(int) 
        }

        if response.data:
            for item in response.data:
                tokens = item.get('total_tokens', 0)
                consumo["total_tokens"] += tokens
                
                data_iso = item.get('data')
                data_formatada = "Data Desconhecida"
                if data_iso:
                    try:
                        data_formatada = datetime.fromisoformat(data_iso.replace('Z', '+00:00')).strftime("%d/%m/%Y %H:%M:%S")
                    except ValueError:
                        try:
                            data_formatada = datetime.strptime(data_iso, "%d/%m/%Y %H:%M:%S").strftime("%d/%m/%Y %H:%M:%S")
                        except ValueError:
                            data_formatada = str(data_iso)
                
                consumo["historico"].append({
                    "tokens": tokens,
                    "tipo": item.get('tipo', 'desconhecido'),
                    "plataforma": item.get('plataforma'),
                    "data": data_formatada
                })
                
                tipo_op = item.get('tipo', 'outro').lower()
                if tipo_op in ["copy", "analise"]:
                    consumo["por_operacao"][tipo_op] += tokens
                else:
                    consumo["por_operacao"]['outro'] += tokens
            
            consumo["historico"].reverse() 

        consumo["por_operacao"] = {
            "copy": consumo["por_operacao"]['copy'],
            "analise": consumo["por_operacao"]['analise'],
            "outro": consumo["por_operacao"]['outro']
        }
        return consumo
        
    except Exception as e:
        st.error(f"Erro ao carregar consumo de tokens do Supabase: {e}")
        return {
            "total_tokens": 0,
            "historico": [],
            "por_operacao": {"copy": 0, "analise": 0, "outro": 0}
        }

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
            try:
                # Adicionar logout do Supabase
                supabase.auth.sign_out()
                st.success("Logout realizado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao fazer logout do Supabase: {e}")
            
            # Limpar estado da sessão do Streamlit
            st.session_state.autenticado = False
            st.session_state.username = None
            st.session_state.login_success = False
            # Limpar outros dados de sessão que dependem do usuário, se houver
            st.session_state.generated_copy = ""
            st.session_state.form_data = {}
            st.session_state.historico = []
            st.session_state.analise_leads = None
            if 'analise_id' in st.session_state:
                del st.session_state['analise_id']

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
                            df_combinado = pd.concat(dfs, ignore_index=True)
                            df_combinado = df_combinado.drop_duplicates()
                            
                            # Ajustar a chamada para receber três valores
                            analise_texto_resultado, analise_db_id_retornado, tempo_proc_openai_retornado = analisar_leads_csv(
                                df_combinado, plataforma_analise, objetivo_analise
                            )
                            
                            if analise_texto_resultado and analise_db_id_retornado:
                                st.session_state.analise_leads_conteudo_ia = analise_texto_resultado
                                st.session_state.analise_id_atual_db = analise_db_id_retornado
                                st.success("Análise concluída e salva no histórico!")
                                
                                # Salvar métricas usando o tempo de processamento retornado
                                # A função salvar_metricas atualmente define "total_tokens": 0 e "tempo_processamento" 
                                # para "analise" baseado no que é passado.
                                metricas_payload_analise = {
                                    "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                    "plataforma": plataforma_analise,
                                    "objetivo": objetivo_analise,
                                    "total_leads": len(df_combinado),
                                    "tempo_processamento": tempo_proc_openai_retornado # Passar o tempo correto
                                }
                                salvar_metricas({"analise": metricas_payload_analise})

                            elif analise_texto_resultado is None and analise_db_id_retornado is None:
                                # Erro já foi mostrado por analisar_leads_csv ou sua helper
                                st.session_state.analise_leads_conteudo_ia = None
                                st.session_state.analise_id_atual_db = None
                            else: # Caso inesperado
                                st.error("Ocorreu um erro inesperado durante a análise.")
                                st.session_state.analise_leads_conteudo_ia = None
                                st.session_state.analise_id_atual_db = None
                
                # Mostrar resultados da análise (usando a nova chave de session_state)
                if st.session_state.get('analise_leads_conteudo_ia'):
                    st.subheader("📊 Resultados da Análise")
                    st.markdown(st.session_state.analise_leads_conteudo_ia)
                    
                    # Seção de feedback - só mostrar se a análise foi salva e temos um ID de DB
                    if st.session_state.get('analise_id_atual_db'):
                        st.subheader("💭 Feedback da Análise")
                        # Usar uma chave de formulário única para evitar conflitos
                        with st.form(f"feedback_form_nova_analise_{st.session_state.analise_id_atual_db}"):
                            pontos_positivos = st.text_area("Pontos Positivos:", 
                                placeholder="O que você achou mais útil nesta análise?", key=f"fp_pos_{st.session_state.analise_id_atual_db}")
                            pontos_melhorar = st.text_area("Pontos a Melhorar:", 
                                placeholder="O que poderia ser melhorado nesta análise?", key=f"fp_neg_{st.session_state.analise_id_atual_db}")
                            nota = st.slider("Nota da Análise:", 1, 5, 3, key=f"fp_nota_{st.session_state.analise_id_atual_db}")
                            feedback_submit = st.form_submit_button("Enviar Feedback")
                            
                            if feedback_submit:
                                feedback_data_payload = {
                                    "pontos_positivos": pontos_positivos,
                                    "pontos_melhorar": pontos_melhorar,
                                    "nota": nota
                                }
                                # Usar o ID UUID do banco de dados armazenado na session_state
                                if salvar_feedback(st.session_state.analise_id_atual_db, feedback_data_payload):
                                    st.success("Feedback enviado com sucesso! Obrigado por ajudar a melhorar nossas análises.")
                                else:
                                    st.error("Falha ao enviar o feedback.")
                    else:
                        if st.session_state.get('analise_leads_conteudo_ia'): # Só mostrar esta msg se houve tentativa de análise
                            st.info("A análise precisa ser salva com sucesso no banco de dados antes de adicionar feedback.")
                    
                    if st.button("📋 Copiar Análise (Resultados)", key=f"copiar_analise_nova_{st.session_state.get('analise_id_atual_db', '')}"):
                        st.code(st.session_state.analise_leads_conteudo_ia)
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