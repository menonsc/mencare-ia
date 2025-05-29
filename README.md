# Mencare IA - Gerador de Copy e Análise de Leads

Aplicação Streamlit para geração de copy e análise de leads usando IA.

## 🚀 Funcionalidades

- Geração de copy para diferentes plataformas
- Análise de leads via CSV
- Dashboard com métricas
- Sistema de feedback
- Histórico de análises
- Tags e categorização

## 🛠️ Tecnologias

- Python 3.8+
- Streamlit
- OpenAI GPT-4
- Supabase (PostgreSQL)
- Plotly

## 📋 Pré-requisitos

- Python 3.8 ou superior
- Conta no Supabase
- Chave da API OpenAI

## 🔧 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/mencare-ia.git
cd mencare-ia
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
Crie um arquivo `.env` na raiz do projeto com:
```
OPENAI_API_KEY=sua_chave_api_openai
SUPABASE_URL=sua_url_supabase
SUPABASE_KEY=sua_chave_supabase
```

5. Configure o banco de dados:
- Acesse o painel do Supabase
- Execute o script `supabase_schema.sql` no SQL Editor

## 🚀 Executando a aplicação

```bash
streamlit run app.py
```

## 📁 Estrutura do Projeto

```
mencare-ia/
├── app.py              # Aplicação principal
├── supabase_config.py  # Configuração do Supabase
├── requirements.txt    # Dependências
├── supabase_schema.sql # Esquema do banco de dados
├── config.yaml         # Configurações de usuários
└── README.md          # Documentação
```

## 🔒 Segurança

- Não compartilhe suas chaves de API
- Mantenha o arquivo `.env` local
- Não comite arquivos sensíveis no GitHub

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes. 