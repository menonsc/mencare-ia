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

## 🗄️ Estrutura do Banco de Dados

O projeto utiliza o Supabase (PostgreSQL) com as seguintes tabelas principais:

- `users`: Armazena informações dos usuários
- `copies`: Armazena as copies geradas
- `analises_leads`: Armazena as análises de leads
- `feedback`: Armazena feedbacks das análises
- `metricas`: Armazena métricas de uso
- `metricas_plataforma`: Armazena métricas específicas por plataforma
- `tags`: Armazena tags para categorização

## 🔧 Troubleshooting

### Problemas Comuns

1. **Erro de Conexão com Supabase**
   - Verifique se as variáveis de ambiente `SUPABASE_URL` e `SUPABASE_KEY` estão configuradas corretamente
   - Confirme se o projeto está ativo no Supabase

2. **Erro de API OpenAI**
   - Verifique se a chave da API está configurada no arquivo `.env`
   - Confirme se a chave tem permissões suficientes

3. **Erro ao Carregar CSV**
   - Verifique se o arquivo está no formato CSV válido
   - Confirme se o arquivo não está corrompido
   - Verifique se o arquivo tem as colunas necessárias

## 🤝 Contribuição

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature (`git checkout -b feature/AmazingFeature`)
3. Faça o Commit das suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Faça o Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Changelog

### v1.0.0
- Lançamento inicial
- Geração de copy com IA
- Análise de leads via CSV
- Dashboard com métricas
- Sistema de feedback
- Histórico de análises
- Tags e categorização

## 📞 Suporte

Para suporte, envie um email para [joaomenonsc@gmail.com] ou abra uma issue no GitHub.

## 🔒 Segurança

- Não compartilhe suas chaves de API
- Mantenha o arquivo `.env` local
- Não comite arquivos sensíveis no GitHub

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.