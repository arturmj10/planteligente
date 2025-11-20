# pip install psycopg2-binary python-dotenv

import psycopg2
from psycopg2 import DatabaseError, OperationalError
import os
from dotenv import load_dotenv
from ai import inserir_medicao_com_analise_ia

# Carrega variáveis do arquivo .env
load_dotenv()

# Para compatibilidade, usamos Exception genérico quando necessário
Error = Exception

# Variáveis
# Valores para criação de tabelas do Banco de Dados
tables = {
    'ESTUFA': (
        """CREATE TABLE estufa (
            id_estufa BIGSERIAL PRIMARY KEY,
            nome VARCHAR(100),
            localizacao VARCHAR(255),
            tamanho NUMERIC(6,2),
            status VARCHAR(50)
        )"""),
    'CULTURA': (
        """CREATE TABLE cultura (
            id_cultura BIGSERIAL PRIMARY KEY,
            nome_popular VARCHAR(100),
            nome_cientifico VARCHAR(100),
            tempo_ciclo_dias INT
        )"""),
    'SENSOR': (
        """CREATE TABLE sensor (
            id_sensor BIGSERIAL PRIMARY KEY,
            unidade_medida VARCHAR(10),
            tipo_sensor VARCHAR(100),
            id_estufa BIGINT,
            CONSTRAINT fk_sensor_estufa FOREIGN KEY (id_estufa) REFERENCES estufa (id_estufa)
        )"""),
    'CONDICAO_IDEAL': (
        """CREATE TABLE condicao_ideal (
            id_condicao BIGSERIAL PRIMARY KEY,
            umid_min NUMERIC(4,2),
            umid_max NUMERIC(4,2),
            temp_min NUMERIC(4,2),
            temp_max NUMERIC(4,2),
            id_cultura BIGINT,
            CONSTRAINT fk_condicaoideal_cultura FOREIGN KEY (id_cultura) REFERENCES cultura (id_cultura)
        )"""),
    'ATUADOR': (
        """CREATE TABLE atuador (
            id_atuador BIGSERIAL PRIMARY KEY,
            tipo_atuador VARCHAR(100),
            capacidade VARCHAR(100),
            id_estufa BIGINT,
            CONSTRAINT fk_atuador_estufa FOREIGN KEY (id_estufa) REFERENCES estufa (id_estufa)
        )"""),
    'RECURSO': (
        """CREATE TABLE recurso (
            id_recurso BIGSERIAL PRIMARY KEY,
            nome_recurso VARCHAR(100),
            tipo_consumo VARCHAR(50)
        )"""),
    'FUNCIONARIO': (
        """CREATE TABLE funcionario (
            id_funcionario BIGSERIAL PRIMARY KEY,
            cpf VARCHAR(11),
            nome VARCHAR(255),
            telefone VARCHAR(15),
            cargo VARCHAR(100)
        )"""),
    'TAREFA': (
        """CREATE TABLE tarefa (
            id_tarefa BIGSERIAL PRIMARY KEY,
            descricao VARCHAR(500),
            data_conclusao TIMESTAMP,
            data_agendada TIMESTAMP,
            id_funcionario BIGINT,
            CONSTRAINT fk_tarefa_funcionario FOREIGN KEY (id_funcionario) REFERENCES funcionario (id_funcionario)
        )"""),
    'MEDICAO': (
        """CREATE TABLE medicao (
            id_medicao BIGSERIAL PRIMARY KEY,
            data_hora_registro TIMESTAMP,
            valor_medido NUMERIC(10,4),
            id_sensor BIGINT,
            CONSTRAINT fk_medicao_sensor FOREIGN KEY (id_sensor) REFERENCES sensor (id_sensor)
        )"""),
    'ALERTA': (
        """CREATE TABLE alerta (
            id_alerta BIGSERIAL PRIMARY KEY,
            seriedade VARCHAR(50),
            mensagem VARCHAR(255),
            data_hora_alerta TIMESTAMP,
            id_medicao BIGINT,
            CONSTRAINT fk_alerta_medicao FOREIGN KEY (id_medicao) REFERENCES medicao (id_medicao)
        )"""),
    'LOTE_PLANTIO': (
        """CREATE TABLE lote_plantio (
            id_lote_plantio BIGSERIAL PRIMARY KEY,
            data_plantio DATE,
            data_previsao_colheita DATE,
            id_estufa BIGINT,
            id_cultura BIGINT,
            CONSTRAINT fk_loteplantio_estufa FOREIGN KEY (id_estufa) REFERENCES estufa (id_estufa),
            CONSTRAINT fk_loteplantio_cultura FOREIGN KEY (id_cultura) REFERENCES cultura (id_cultura)
        )"""),
    'CONSUMO': (
        """CREATE TABLE consumo (
            id_consumo BIGSERIAL PRIMARY KEY,
            data_hora_consumo TIMESTAMP,
            quantidade_consumida NUMERIC(10,4),
            id_atuador BIGINT,
            id_recurso BIGINT,
            CONSTRAINT fk_consumo_atuador FOREIGN KEY (id_atuador) REFERENCES atuador (id_atuador),
            CONSTRAINT fk_consumo_recurso FOREIGN KEY (id_recurso) REFERENCES recurso (id_recurso)
        )"""),
    'ESTUFA_FUNCIONARIO': (
        """CREATE TABLE estufa_funcionario (
            id_estufa_funcionario BIGSERIAL PRIMARY KEY,
            data_inicio DATE NOT NULL,
            data_fim DATE,
            id_funcionario BIGINT,
            id_estufa BIGINT,
            CONSTRAINT uq_estufa_funcionario UNIQUE (data_inicio, id_funcionario, id_estufa),
            CONSTRAINT fk_estufa_funcionario_funcionario FOREIGN KEY (id_funcionario) REFERENCES funcionario (id_funcionario),
            CONSTRAINT fk_estufa_funcionario_estufa FOREIGN KEY (id_estufa) REFERENCES estufa (id_estufa)
        )"""),
}

# Valores para serem inseridos no Banco de Dados
inserts = {
    'ESTUFA': (
        """INSERT INTO estufa (nome, localizacao, tamanho, status) VALUES 
        ('Estufa A', 'Setor Norte - Lote 1', 150.50, 'Ativa'),
        ('Estufa B', 'Setor Sul - Lote 3', 200.00, 'Ativa'),
        ('Estufa C', 'Setor Leste - Lote 5', 175.75, 'Manutenção'),
        ('Estufa D', 'Setor Oeste - Lote 2', 180.00, 'Ativa'),
        ('Estufa E', 'Setor Central - Lote 4', 220.25, 'Inativa')"""),
    'CULTURA': (
        """INSERT INTO cultura (nome_popular, nome_cientifico, tempo_ciclo_dias) VALUES
        ('Tomate', 'Solanum lycopersicum', 90),
        ('Alface', 'Lactuca sativa', 45),
        ('Pimentão', 'Capsicum annuum', 75),
        ('Pepino', 'Cucumis sativus', 60),
        ('Morango', 'Fragaria × ananassa', 120),
        ('Rúcula', 'Eruca sativa', 40),
        ('Espinafre', 'Spinacia oleracea', 50),
        ('Couve', 'Brassica oleracea', 65),
        ('Cenoura', 'Daucus carota', 70),
        ('Rabanete', 'Raphanus sativus', 30)"""),
    'SENSOR': (
        """INSERT INTO sensor (unidade_medida, tipo_sensor, id_estufa) VALUES
        ('°C', 'Temperatura', 1),
        ('%', 'Umidade', 1),
        ('°C', 'Temperatura', 2),
        ('%', 'Umidade', 2),
        ('lux', 'Luminosidade', 1),
        ('lux', 'Luminosidade', 2),
        ('°C', 'Temperatura', 3),
        ('%', 'Umidade', 3),
        ('pH', 'pH do Solo', 1),
        ('pH', 'pH do Solo', 2),
        ('lux', 'Luminosidade', 3),
        ('pH', 'pH do Solo', 3),
        ('°C', 'Temperatura', 4),
        ('%', 'Umidade', 4),
        ('lux', 'Luminosidade', 4),
        ('pH', 'pH do Solo', 4),
        ('°C', 'Temperatura', 5),
        ('%', 'Umidade', 5),
        ('lux', 'Luminosidade', 5),
        ('pH', 'pH do Solo', 5)"""),
    'CONDICAO_IDEAL': (
        """INSERT INTO condicao_ideal (umid_min, umid_max, temp_min, temp_max, id_cultura) VALUES
        (60.00, 80.00, 18.00, 28.00, 1),
        (70.00, 85.00, 15.00, 22.00, 2),
        (60.00, 75.00, 20.00, 30.00, 3),
        (65.00, 80.00, 20.00, 28.00, 4),
        (70.00, 85.00, 18.00, 24.00, 5),
        (65.00, 80.00, 15.00, 20.00, 6),
        (70.00, 85.00, 15.00, 22.00, 7),
        (65.00, 80.00, 16.00, 24.00, 8),
        (60.00, 75.00, 15.00, 25.00, 9),
        (65.00, 80.00, 15.00, 20.00, 10)"""),
    'ATUADOR': (
        """INSERT INTO atuador (tipo_atuador, capacidade, id_estufa) VALUES
        ('Irrigação', '100 L/h', 1),
        ('Ventilação', '500 m³/h', 1),
        ('Irrigação', '150 L/h', 2),
        ('Ventilação', '600 m³/h', 2),
        ('Aquecimento', '5000 W', 1),
        ('Aquecimento', '6000 W', 2),
        ('Irrigação', '120 L/h', 3),
        ('Ventilação', '550 m³/h', 3),
        ('Aquecimento', '5500 W', 3),
        ('Irrigação', '130 L/h', 4),
        ('Ventilação', '580 m³/h', 4),
        ('Aquecimento', '5800 W', 4),
        ('Irrigação', '160 L/h', 5),
        ('Ventilação', '650 m³/h', 5),
        ('Aquecimento', '6500 W', 5)"""),
    'RECURSO': (
        """INSERT INTO recurso (nome_recurso, tipo_consumo) VALUES
        ('Água', 'Litros'),
        ('Energia Elétrica', 'kWh'),
        ('Fertilizante NPK', 'Kg'),
        ('Gás', 'm³'),
        ('Adubo Orgânico', 'Kg'),
        ('Calcário', 'Kg'),
        ('Pesticida Orgânico', 'Litros')"""),
    'FUNCIONARIO': (
        """INSERT INTO funcionario (cpf, nome, telefone, cargo) VALUES
        ('12345678901', 'João Silva Santos', '(47)99999-1111', 'Técnico Agrícola'),
        ('23456789012', 'Maria Oliveira Costa', '(47)99999-2222', 'Engenheira Agrônoma'),
        ('34567890123', 'Pedro Souza Lima', '(47)99999-3333', 'Operador de Estufa'),
        ('45678901234', 'Ana Paula Ferreira', '(47)99999-4444', 'Supervisora'),
        ('56789012345', 'Carlos Alberto Rocha', '(47)99999-5555', 'Técnico de Manutenção'),
        ('67890123456', 'Juliana Martins Silva', '(47)99999-6666', 'Operadora de Estufa'),
        ('78901234567', 'Roberto Carlos Dias', '(47)99999-7777', 'Técnico Agrícola'),
        ('89012345678', 'Fernanda Lima Santos', '(47)99999-8888', 'Auxiliar Administrativo')"""),
    'TAREFA': (
        """INSERT INTO tarefa (descricao, data_conclusao, data_agendada, id_funcionario) VALUES
        ('Verificar sistema de irrigação da Estufa A', '2024-11-10 14:30:00', '2024-11-10 08:00:00', 1),
        ('Calibrar sensores de temperatura', NULL, '2025-11-21 09:00:00', 5),
        ('Colheita de alface na Estufa B', '2024-11-12 11:00:00', '2024-11-12 07:00:00', 3),
        ('Inspeção geral das estufas', NULL, '2025-11-21 10:00:00', 2),
        ('Manutenção preventiva dos atuadores', '2024-11-14 16:00:00', '2024-11-14 13:00:00', 5),
        ('Aplicação de fertilizante NPK na Estufa C', NULL, '2025-11-22 08:00:00', 1),
        ('Limpeza dos filtros de ventilação', '2024-11-13 15:00:00', '2024-11-13 14:00:00', 5),
        ('Plantio de tomates na Estufa D', '2024-11-11 10:30:00', '2024-11-11 08:00:00', 3),
        ('Verificação de pH do solo', NULL, '2025-11-23 09:00:00', 1),
        ('Troca de lâmpadas LED', '2024-11-15 11:00:00', '2024-11-15 10:00:00', 5),
        ('Monitoramento de pragas', NULL, '2025-11-20 08:00:00', 2),
        ('Poda de plantas na Estufa A', '2024-11-14 13:00:00', '2024-11-14 09:00:00', 3),
        ('Ajuste de sistemas de aquecimento', NULL, '2025-11-21 10:00:00', 5),
        ('Colheita de pimentões na Estufa C', NULL, '2025-11-22 07:00:00', 3),
        ('Análise de qualidade da água', '2024-11-13 16:00:00', '2024-11-13 14:00:00', 2)"""),
    'MEDICAO': (
        """INSERT INTO medicao (data_hora_registro, valor_medido, id_sensor) VALUES
        ('2025-11-15 08:00:00', 22.5, 1),
        ('2025-11-15 08:00:00', 75.3, 2),
        ('2025-11-15 08:00:00', 21.8, 3),
        ('2025-11-15 08:00:00', 78.2, 4),
        ('2025-11-15 12:00:00', 26.3, 1),
        ('2025-11-15 12:00:00', 68.5, 2),
        ('2025-11-15 12:00:00', 25.1, 3),
        ('2025-11-15 12:00:00', 72.0, 4),
        ('2025-11-15 08:00:00', 6.8, 9),
        ('2025-11-15 08:00:00', 6.5, 10),
        ('2025-11-15 16:00:00', 24.8, 1),
        ('2025-11-15 16:00:00', 71.2, 2),
        ('2025-11-15 16:00:00', 23.5, 3),
        ('2025-11-15 16:00:00', 74.8, 4),
        ('2025-11-15 08:00:00', 850.5, 5),
        ('2025-11-15 08:00:00', 920.3, 6),
        ('2025-11-15 12:00:00', 1250.8, 5),
        ('2025-11-15 12:00:00', 1380.2, 6),
        ('2025-11-15 08:00:00', 20.5, 7),
        ('2025-11-15 08:00:00', 80.2, 8),
        ('2025-11-14 08:00:00', 21.8, 1),
        ('2025-11-14 08:00:00', 76.5, 2),
        ('2025-11-14 12:00:00', 25.2, 1),
        ('2025-11-14 12:00:00', 70.3, 2),
        ('2025-11-14 16:00:00', 23.9, 1),
        ('2025-11-14 16:00:00', 73.1, 2),
        ('2025-11-13 08:00:00', 22.1, 1),
        ('2025-11-13 08:00:00', 77.8, 2),
        ('2025-11-13 12:00:00', 26.5, 1),
        ('2025-11-13 12:00:00', 67.2, 2)"""),
    'ALERTA': (
        """INSERT INTO alerta (seriedade, mensagem, data_hora_alerta, id_medicao) VALUES
        ('Média', 'Temperatura acima do ideal', '2025-11-15 12:05:00', 5),
        ('Baixa', 'Umidade abaixo do recomendado', '2025-11-15 12:05:00', 6),
        ('Alta', 'Temperatura crítica detectada', '2025-11-13 12:05:00', 29),
        ('Média', 'Umidade fora da faixa ideal', '2025-11-13 12:05:00', 30),
        ('Baixa', 'Luminosidade levemente baixa', '2025-11-15 08:05:00', 15),
        ('Média', 'pH do solo necessita correção', '2025-11-15 08:05:00', 9)"""),
    'LOTE_PLANTIO': (
        """INSERT INTO lote_plantio (data_plantio, data_previsao_colheita, id_estufa, id_cultura) VALUES
        ('2025-09-01', '2025-12-30', 1, 1), 
        ('2025-10-15', '2025-12-30', 2, 2),
        ('2025-09-20', '2026-01-05', 1, 3), 
        ('2025-10-01', '2025-12-30', 2, 4),
        ('2025-08-15', '2026-01-15', 4, 5),
        ('2025-10-20', '2025-12-30', 3, 6),
        ('2025-09-25', '2025-12-15', 2, 7),
        ('2025-09-10', '2025-12-15', 4, 8),
        ('2025-09-05', '2025-12-15', 3, 9),
        ('2025-10-25', '2025-12-25', 1, 10)"""), 
    'CONSUMO': (
        """INSERT INTO consumo (data_hora_consumo, quantidade_consumida, id_atuador, id_recurso) VALUES
        ('2025-11-15 08:00:00', 50.5, 1, 1),
        ('2025-11-15 08:00:00', 3.2, 2, 2),
        ('2025-11-15 12:00:00', 45.0, 1, 1),
        ('2025-11-15 12:00:00', 2.8, 2, 2),
        ('2025-11-15 06:00:00', 5.5, 5, 2),
        ('2025-11-15 18:00:00', 6.2, 5, 2),
        ('2025-11-15 10:00:00', 75.0, 3, 1),
        ('2025-11-15 14:00:00', 4.1, 4, 2),
        ('2025-11-15 08:00:00', 2.5, 1, 3),
        ('2025-11-15 09:00:00', 60.0, 7, 1),
        ('2025-11-15 11:00:00', 3.5, 8, 2),
        ('2025-11-15 13:00:00', 5.8, 9, 2),
        ('2025-11-15 15:00:00', 55.0, 10, 1),
        ('2025-11-15 16:00:00', 3.9, 11, 2),
        ('2025-11-14 08:00:00', 48.5, 1, 1),
        ('2025-11-14 08:00:00', 3.1, 2, 2),
        ('2025-11-14 12:00:00', 52.0, 3, 1),
        ('2025-11-14 12:00:00', 3.6, 4, 2),
        ('2025-11-14 10:00:00', 1.8, 3, 3),
        ('2025-11-14 14:00:00', 3.2, 1, 5)"""),
    'ESTUFA_FUNCIONARIO': (
        """INSERT INTO estufa_funcionario (data_inicio, data_fim, id_funcionario, id_estufa) VALUES
        ('2025-01-01', NULL, 1, 1),
        ('2025-01-01', NULL, 2, 1),
        ('2025-02-01', NULL, 3, 2),
        ('2025-01-01', NULL, 4, 2),
        ('2025-03-01', '2025-10-31', 5, 3),
        ('2025-11-01', NULL, 5, 1),
        ('2025-02-15', NULL, 6, 3),
        ('2025-03-10', NULL, 7, 4),
        ('2025-01-20', NULL, 1, 4),
        ('2025-04-01', '2025-09-30', 3, 5),
        ('2025-10-01', NULL, 6, 5)""")
}

# Valores para deletar as tabelas (ordem reversa devido às dependências)
drop = {
    'ESTUFA_FUNCIONARIO': "DROP TABLE IF EXISTS estufa_funcionario",
    'CONSUMO': "DROP TABLE IF EXISTS consumo",
    'LOTE_PLANTIO': "DROP TABLE IF EXISTS lote_plantio",
    'ALERTA': "DROP TABLE IF EXISTS alerta",
    'MEDICAO': "DROP TABLE IF EXISTS medicao",
    'TAREFA': "DROP TABLE IF EXISTS tarefa",
    'FUNCIONARIO': "DROP TABLE IF EXISTS funcionario",
    'RECURSO': "DROP TABLE IF EXISTS recurso",
    'ATUADOR': "DROP TABLE IF EXISTS atuador",
    'CONDICAO_IDEAL': "DROP TABLE IF EXISTS condicao_ideal",
    'SENSOR': "DROP TABLE IF EXISTS sensor",
    'CULTURA': "DROP TABLE IF EXISTS cultura",
    'ESTUFA': "DROP TABLE IF EXISTS estufa"
}

# Valores para teste de update
update = {
    'ESTUFA': (
        """UPDATE estufa
        SET status = 'Ativa',
            tamanho = 225.50
        WHERE id_estufa = 3"""),
    'FUNCIONARIO': (
        """UPDATE funcionario
        SET telefone = '(47)99999-6666',
            cargo = 'Técnico Agrícola Sênior'
        WHERE id_funcionario = 1"""),
    'TAREFA': (
        """UPDATE tarefa
        SET data_conclusao = '2024-11-16 15:30:00'
        WHERE id_tarefa = 2"""),
    'MEDICAO': (
        """UPDATE medicao
        SET valor_medido = 23.5
        WHERE id_medicao = 1"""),
    'SENSOR': (
        """UPDATE sensor
        SET tipo_sensor = 'Temperatura e Umidade'
        WHERE id_sensor = 7"""),
    'CULTURA': (
        """UPDATE cultura
        SET tempo_ciclo_dias = 95
        WHERE id_cultura = 1""")
}

# Valores para teste de delete
delete = {
    'ALERTA': (
        """DELETE FROM alerta
        WHERE seriedade = 'Baixa'"""),
    'CONSUMO': (
        """DELETE FROM consumo
        WHERE quantidade_consumida < 3.0"""),
    'TAREFA': (
        """DELETE FROM tarefa
        WHERE data_conclusao IS NOT NULL AND data_conclusao < '2024-11-14'""")
}


# Funções
def connect_estufa():
    try:
        cnx = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5433'),
            database=os.getenv('DB_NAME', 'planteligente'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'admin')
        )
        print("Conectado ao servidor PostgreSQL")
        cursor = cnx.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print("Versão do PostgreSQL:", db_version[0])
        print("Conectado ao banco de dados estufa_db")
        cursor.close()
        return cnx
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        return None


def drop_all_tables(connect):
    print("\n---DROP DB---")
    cursor = connect.cursor()
    for drop_name in drop:
        drop_description = drop[drop_name]
        try:
            print(f"Drop {drop_name}: ", end='')
            cursor.execute(drop_description)
        except Error as err:
            print(err)
        else:
            print("OK")
    connect.commit()
    cursor.close()


def create_all_tables(connect):
    print("\n---CREATE ALL TABLES---")
    cursor = connect.cursor()
    for table_name in tables:
        table_description = tables[table_name]
        try:
            print(f"Criando tabela {table_name}: ", end='')
            cursor.execute(table_description)
        except Error as err:
            print(err)
        else:
            print("OK")
    connect.commit()
    cursor.close()


def show_table(connect):
    print("\n---SELECIONAR TABELA---")
    cursor = connect.cursor()
    # Lista os nomes das tabelas disponíveis
    available_tables = list(tables.keys())
    print("Tabelas disponíveis:")
    for table_name in available_tables:
        print(f"- {table_name}")
        
    try:
        name = input("\nDigite o nome da tabela que deseja consultar: ").upper()
        
        if name not in available_tables:
            print(f"❌ Erro: Tabela '{name}' não encontrada ou indisponível.")
            return

        select = f"SELECT * FROM {name.lower()}"
        cursor.execute(select)
        
        # --- NOVO TRECHO PARA MOSTRAR OS NOMES DAS COLUNAS ---
        print(f"\nTABELA {name}")
        
        # Obtém os nomes das colunas usando cursor.description
        # Cada tupla em cursor.description contém (name, type_code, ...)
        column_names = [desc[0] for desc in cursor.description]
        
        # Imprime os nomes das colunas para indicar o significado de cada dado
        print("COLUNAS:")
        print(column_names)
        print("-" * 50) # Separador visual

        # --- FIM DO NOVO TRECHO ---
        
        myresult = cursor.fetchall()
        if myresult:
            for x in myresult:
                print(x)
        else:
            print("Tabela vazia")
            
    except Error as err:
        print(f"❌ Erro ao consultar a tabela: {err}")
    finally:
        cursor.close()


def insert_value(connect):
    print("\n---SELECIONAR TABELA PARA INSERÇÃO---")
    cursor = connect.cursor()
    for table_name in tables:
        print(f"Nome: {table_name}")
    try:
        name = input("\nDigite o nome da tabela que deseja inserir dados: ").upper()
        for table_name in tables:
            table_description = tables[table_name]
            if table_name == name:
                print(f"Estrutura da tabela {table_name}:\n{table_description}")
        
        print("\nDigite os valores separados por vírgula (use aspas simples para texto)")
        print("Exemplo: 'Estufa F', 'Setor Norte', 300.00, 'Ativa'")
        valores = input("Valores: ")
        
        sql = f"INSERT INTO {name.lower()} VALUES ({valores})"
        cursor.execute(sql)
    except Error as err:
        print(err)
    else:
        print("Registro inserido com sucesso")
    connect.commit()
    cursor.close()


def update_value(connect):
    print("\n---SELECIONAR TABELA PARA ATUALIZAÇÃO---")
    cursor = connect.cursor()
    for table_name in tables:
        print(f"Nome: {table_name}")
    try:
        name = input("\nDigite o nome da tabela que deseja atualizar: ").upper()
        for table_name in tables:
            table_description = tables[table_name]
            if table_name == name:
                print(f"Para criar a tabela: {table_name}, foi utilizado o seguinte código: {table_description}")
        atributo = input("Digite o atributo a ser alterado: ")
        valor = input("Digite o valor a ser atribuído (use aspas simples para texto): ")
        codigo_f = input("Digite a coluna da chave primária: ")
        codigo = input("Digite o valor numérico do campo da chave primária: ")
        sql = f"UPDATE {name.lower()} SET {atributo} = {valor} WHERE {codigo_f} = {codigo}"
        cursor.execute(sql)
    except Error as err:
        print(err)
    else:
        print("Atributo atualizado")
    connect.commit()
    cursor.close()


def delete_value(connect):
    print("\n---SELECIONAR TABELA PARA DELEÇÃO---")
    cursor = connect.cursor()
    for table_name in tables:
        print(f"Nome: {table_name}")
    try:
        name = input("\nDigite o nome da tabela que deseja deletar dados: ").upper()
        for table_name in tables:
            table_description = tables[table_name]
            if table_name == name:
                print(f"Estrutura da tabela {table_name}:\n{table_description}")
        
        codigo_f = input("Digite a coluna para condição de deleção: ")
        codigo = input("Digite o valor para a condição (use aspas simples para texto): ")
        
        sql = f"DELETE FROM {name.lower()} WHERE {codigo_f} = {codigo}"
        cursor.execute(sql)
        
        print(f"Registros deletados: {cursor.rowcount}")
    except Error as err:
        print(err)
    else:
        print("Deleção concluída")
    connect.commit()
    cursor.close()


def insert_test(connect):
    print("\n---INSERT TEST---")
    cursor = connect.cursor()
    for insert_name in inserts:
        insert_description = inserts[insert_name]
        try:
            print(f"Inserindo valores para {insert_name}: ", end='')
            cursor.execute(insert_description)
        except Error as err:
            print(err)
        else:
            print("OK")
    connect.commit()
    cursor.close()


def update_test(connect):
    print("\n---UPDATE TEST---")
    cursor = connect.cursor()
    for update_name in update:
        update_description = update[update_name]
        try:
            print(f"Teste de atualização de valores para {update_name}: ", end='')
            cursor.execute(update_description)
        except Error as err:
            print(err)
        else:
            print("OK")
    connect.commit()
    cursor.close()


def delete_test(connect):
    print("\n---DELETE TEST---")
    cursor = connect.cursor()
    for delete_name in delete:
        delete_description = delete[delete_name]
        try:
            print(f"Teste de deleção de valores para {delete_name}: ", end='')
            cursor.execute(delete_description)
        except Error as err:
            print(err)
        else:
            print("OK")
    connect.commit()
    cursor.close()


def consulta1(connect):
    select_query = """
    SELECT
        e.nome AS estufa,
        r.nome_recurso AS recurso,
        SUM(c.quantidade_consumida) AS total_consumido
    FROM
        estufa e
    JOIN
        atuador a ON e.id_estufa = a.id_estufa
    JOIN
        consumo c ON a.id_atuador = c.id_atuador
    JOIN
        recurso r ON c.id_recurso = r.id_recurso
    GROUP BY
        e.nome, r.nome_recurso
    ORDER BY
        e.nome, total_consumido DESC
    """
    print("\nPrimeira Consulta: Consumo por recurso e estufa")
    cursor = connect.cursor()
    cursor.execute(select_query)
    myresult = cursor.fetchall()
    for x in myresult:
        print(x)
    cursor.close()


def consulta2(connect):
    select_query = """
    SELECT
        f.nome AS nome_funcionario,
        e.nome AS estufa,
        COUNT(al.id_alerta) AS quantidade_alertas_criticos
    FROM
        funcionario f
    JOIN
        estufa_funcionario ef ON f.id_funcionario = ef.id_funcionario
    JOIN
        estufa e ON ef.id_estufa = e.id_estufa
    JOIN
        sensor s ON e.id_estufa = s.id_estufa
    JOIN
        medicao m ON s.id_sensor = m.id_sensor
    JOIN
        alerta al ON m.id_medicao = al.id_medicao
    WHERE
        al.seriedade = 'Alta'
    GROUP BY
        f.nome, e.nome
    HAVING
        COUNT(al.id_alerta) > 0
    ORDER BY
        f.nome, quantidade_alertas_criticos DESC
    """
    print("\nSegunda Consulta: Alertas críticos por funcionário e estufa")
    cursor = connect.cursor()
    cursor.execute(select_query)
    myresult = cursor.fetchall()
    for x in myresult:
        print(x)
    cursor.close()


def consulta3(connect):
    select_query = """
    SELECT
        c.nome_popular AS cultura,
        e.nome AS estufa,
        AVG(ABS(m.valor_medido - ((ci.temp_min + ci.temp_max) / 2))) AS desvio_medio_temperatura
    FROM
        cultura c
    JOIN
        condicao_ideal ci ON c.id_cultura = ci.id_cultura
    JOIN
        lote_plantio lp ON c.id_cultura = lp.id_cultura
    JOIN
        estufa e ON lp.id_estufa = e.id_estufa
    JOIN
        sensor s ON e.id_estufa = s.id_estufa
    JOIN
        medicao m ON s.id_sensor = m.id_sensor
    WHERE
        s.tipo_sensor = 'Temperatura' AND m.valor_medido IS NOT NULL
    GROUP BY
        c.nome_popular, e.nome
    ORDER BY
        desvio_medio_temperatura DESC
    """
    print("\nTerceira Consulta: Desvio médio de temperatura por cultura")
    cursor = connect.cursor()
    cursor.execute(select_query)
    myresult = cursor.fetchall()
    for x in myresult:
        print(x)
    cursor.close()


def consulta_extra(connect):
    select_query = """
    SELECT 
        e.nome AS estufa,
        COUNT(DISTINCT a.id_alerta) AS total_alertas,
        COUNT(DISTINCT CASE WHEN a.seriedade = 'Alta' THEN a.id_alerta END) AS alertas_alta,
        COUNT(DISTINCT CASE WHEN a.seriedade = 'Média' THEN a.id_alerta END) AS alertas_media,
        COUNT(DISTINCT CASE WHEN a.seriedade = 'Baixa' THEN a.id_alerta END) AS alertas_baixa
    FROM estufa e
    LEFT JOIN sensor s ON e.id_estufa = s.id_estufa
    LEFT JOIN medicao m ON s.id_sensor = m.id_sensor
    LEFT JOIN alerta a ON m.id_medicao = a.id_medicao
    WHERE e.status = 'Ativa'
    GROUP BY e.nome
    ORDER BY total_alertas DESC
    """
    print("\nConsulta Extra: Quantidade de alertas por estufa ativa, classificados por seriedade")
    cursor = connect.cursor()
    cursor.execute(select_query)
    myresult = cursor.fetchall()
    for x in myresult:
        print(x)
    cursor.close()


def inserir_medicao_com_ia(connect):
    """Nova função para inserir medição e analisar com IA"""
    print("\n---INSERIR MEDIÇÃO COM ANÁLISE IA---")
    try:
        id_sensor = int(input("ID do Sensor: "))
        valor = float(input("Valor medido: "))
        inserir_medicao_com_analise_ia(connect, id_sensor, valor)
    except ValueError:
        print("❌ Erro: Digite valores numéricos válidos")
    except Exception as e:
        print(f"❌ Erro: {e}")


def exit_db(connect):
    print("\n---EXIT DB---")
    connect.close()
    print("Conexão com o banco de dados foi encerrada!")


def crud_estufa(connect):
    drop_all_tables(connect)
    create_all_tables(connect)
    insert_test(connect)

    print("\n---CONSULTAS BEFORE---")
    consulta1(connect)
    consulta2(connect)
    consulta3(connect)
    consulta_extra(connect)

    update_test(connect)
    delete_test(connect)

    print("\n---CONSULTAS AFTER---")
    consulta1(connect)
    consulta2(connect)
    consulta3(connect)
    consulta_extra(connect)


# Main
try:
    # Estabelece Conexão com o DB
    con = connect_estufa()
    
    if con is None:
        print("Não foi possível conectar ao banco de dados.")
        exit(1)

    power_up = 1
    while power_up == 1:
        interface = """\n       ---MENU---
        1.  CRUD ESTUFA COMPLETO
        2.  TESTE - Create all tables
        3.  TESTE - Insert all values
        4.  TESTE - Update
        5.  TESTE - Delete
        6.  CONSULTA 01
        7.  CONSULTA 02
        8.  CONSULTA 03
        9.  CONSULTA EXTRA
        10. CONSULTA TABELAS INDIVIDUAIS
        11. INSERT VALUES (Manual)
        12. UPDATE VALUES (Manual)
        13. DELETE VALUES (Manual)
        14. CLEAR ALL ESTUFA
        15. 🤖 INSERIR MEDIÇÃO COM ANÁLISE IA
        0.  DISCONNECT DB\n """
        print(interface)

        choice = int(input("Opção: "))
        if choice < 0 or choice > 15:
            print("Erro tente novamente!")
            continue

        if choice == 0:
            exit_db(con)
            print("Muito obrigada(o).")
            break

        if choice == 1:
            crud_estufa(con)

        if choice == 2:
            create_all_tables(con)

        if choice == 3:
            insert_test(con)

        if choice == 4:
            update_test(con)

        if choice == 5:
            delete_test(con)

        if choice == 6:
            consulta1(con)

        if choice == 7:
            consulta2(con)

        if choice == 8:
            consulta3(con)

        if choice == 9:
            consulta_extra(con)

        if choice == 10:
            show_table(con)

        if choice == 11:
            insert_value(con)

        if choice == 12:
            update_value(con)

        if choice == 13:
            delete_value(con)

        if choice == 14:
            drop_all_tables(con)

        if choice == 15:
            inserir_medicao_com_ia(con)

    con.close()

except Error as err:
    print(f"Erro na conexão com o banco de dados: {err}")