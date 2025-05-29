CREATE EXTENSION IF NOT EXISTS "uuid-ossp";



-- Tabela de Copies
CREATE TABLE copies (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    plataforma TEXT NOT NULL,
    objetivo TEXT NOT NULL,
    publico_alvo TEXT NOT NULL,
    produto_servico TEXT NOT NULL,
    tom_de_voz TEXT NOT NULL,
    cta TEXT NOT NULL,
    copy_gerada TEXT NOT NULL,
    data_geracao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    usuario_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Análises de Leads
CREATE TABLE analises_leads (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    data TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    plataforma TEXT NOT NULL,
    objetivo TEXT NOT NULL,
    total_leads INTEGER NOT NULL,
    colunas JSONB NOT NULL,
    analise TEXT NOT NULL,
    tempo_processamento FLOAT NOT NULL,
    resumo_estatistico JSONB NOT NULL,
    usuario_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Feedback
CREATE TABLE feedback (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    analise_id UUID REFERENCES analises_leads(id),
    data TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    pontos_positivos TEXT,
    pontos_melhorar TEXT,
    nota INTEGER CHECK (nota >= 1 AND nota <= 5),
    editado BOOLEAN DEFAULT FALSE,
    ultima_edicao TIMESTAMP WITH TIME ZONE,
    historico_edicoes JSONB DEFAULT '[]'::jsonb,
    usuario_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Métricas
CREATE TABLE metricas (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    data TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tipo TEXT NOT NULL,
    total_tokens INTEGER DEFAULT 0,
    plataforma TEXT NOT NULL,
    tempo_processamento FLOAT DEFAULT 0,
    usuario_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Métricas por Plataforma
CREATE TABLE metricas_plataforma (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    data TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    plataforma TEXT NOT NULL,
    metricas JSONB NOT NULL,
    usuario_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Tags
CREATE TABLE tags (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    analise_id UUID REFERENCES analises_leads(id),
    categoria TEXT NOT NULL,
    tag TEXT NOT NULL,
    usuario_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Função para atualizar o updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para atualizar o updated_at
CREATE TRIGGER update_copies_updated_at
    BEFORE UPDATE ON copies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analises_leads_updated_at
    BEFORE UPDATE ON analises_leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feedback_updated_at
    BEFORE UPDATE ON feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metricas_updated_at
    BEFORE UPDATE ON metricas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_metricas_plataforma_updated_at
    BEFORE UPDATE ON metricas_plataforma
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tags_updated_at
    BEFORE UPDATE ON tags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Habilitar RLS (Row Level Security)
ALTER TABLE copies ENABLE ROW LEVEL SECURITY;
ALTER TABLE analises_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE metricas ENABLE ROW LEVEL SECURITY;
ALTER TABLE metricas_plataforma ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;

-- Políticas de segurança
CREATE POLICY "Usuários podem ver suas próprias copies"
    ON copies FOR SELECT
    USING (usuario_id = auth.uid()::text);

CREATE POLICY "Usuários podem inserir suas próprias copies"
    ON copies FOR INSERT
    WITH CHECK (usuario_id = auth.uid()::text);

CREATE POLICY "Usuários podem atualizar suas próprias copies"
    ON copies FOR UPDATE
    USING (usuario_id = auth.uid()::text);

-- Repetir políticas similares para outras tabelas
CREATE POLICY "Usuários podem ver suas próprias análises"
    ON analises_leads FOR SELECT
    USING (usuario_id = auth.uid()::text);

CREATE POLICY "Usuários podem inserir suas próprias análises"
    ON analises_leads FOR INSERT
    WITH CHECK (usuario_id = auth.uid()::text);

CREATE POLICY "Usuários podem atualizar suas próprias análises"
    ON analises_leads FOR UPDATE
    USING (usuario_id = auth.uid()::text);

-- Índices para melhorar performance
CREATE INDEX idx_copies_usuario_id ON copies(usuario_id);
CREATE INDEX idx_analises_leads_usuario_id ON analises_leads(usuario_id);
CREATE INDEX idx_feedback_usuario_id ON feedback(usuario_id);
CREATE INDEX idx_metricas_usuario_id ON metricas(usuario_id);
CREATE INDEX idx_metricas_plataforma_usuario_id ON metricas_plataforma(usuario_id);
CREATE INDEX idx_tags_usuario_id ON tags(usuario_id); 