from supabase import create_client
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializar cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase_client():
    """Retorna o cliente Supabase configurado"""
    return supabase

# Funções auxiliares para interagir com o Supabase

def salvar_copy(data):
    """Salva uma copy no Supabase"""
    try:
        response = supabase.table('copies').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro ao salvar copy: {e}")
        return None

def salvar_analise(data):
    """Salva uma análise de leads no Supabase"""
    try:
        response = supabase.table('analises_leads').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro ao salvar análise: {e}")
        return None

def salvar_feedback(data):
    """Salva um feedback no Supabase"""
    try:
        response = supabase.table('feedback').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro ao salvar feedback: {e}")
        return None

def salvar_metricas(data):
    """Salva métricas no Supabase"""
    try:
        response = supabase.table('metricas').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro ao salvar métricas: {e}")
        return None

def salvar_metricas_plataforma(data):
    """Salva métricas de plataforma no Supabase"""
    try:
        response = supabase.table('metricas_plataforma').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro ao salvar métricas de plataforma: {e}")
        return None

def salvar_tags(data):
    """Salva tags no Supabase"""
    try:
        response = supabase.table('tags').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro ao salvar tags: {e}")
        return None

def buscar_copies(usuario_id):
    """Busca todas as copies de um usuário"""
    try:
        response = supabase.table('copies').select('*').eq('usuario_id', usuario_id).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar copies: {e}")
        return []

def buscar_analises(usuario_id):
    """Busca todas as análises de um usuário"""
    try:
        response = supabase.table('analises_leads').select('*').eq('usuario_id', usuario_id).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar análises: {e}")
        return []

def buscar_feedback(analise_id):
    """Busca feedback de uma análise específica"""
    try:
        response = supabase.table('feedback').select('*').eq('analise_id', analise_id).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar feedback: {e}")
        return []

def buscar_metricas(usuario_id):
    """Busca métricas de um usuário"""
    try:
        response = supabase.table('metricas').select('*').eq('usuario_id', usuario_id).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar métricas: {e}")
        return []

def buscar_metricas_plataforma(usuario_id):
    """Busca métricas de plataforma de um usuário"""
    try:
        response = supabase.table('metricas_plataforma').select('*').eq('usuario_id', usuario_id).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar métricas de plataforma: {e}")
        return []

def buscar_tags(analise_id):
    """Busca tags de uma análise específica"""
    try:
        response = supabase.table('tags').select('*').eq('analise_id', analise_id).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar tags: {e}")
        return [] 