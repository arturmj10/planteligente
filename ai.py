# ai_monitor.py
# pip install google-generativeai

import google.generativeai as genai
from datetime import datetime, timedelta
import statistics

# Configuração da API do Gemini
GEMINI_API_KEY = "SUA_CHAVE_API_AQUI"

try:
    genai.configure(api_key=GEMINI_API_KEY)
    IA_DISPONIVEL = True
except:
    IA_DISPONIVEL = False
    print("⚠ API do Gemini não configurada.")


class AIGreenhouseMonitor:
    def __init__(self, connection):
        self.connection = connection
        if IA_DISPONIVEL:
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
    
    def get_ultimas_medicoes_sensor(self, id_sensor, tipo_sensor, id_estufa, limit=5):
        """Obtém as últimas N medições do mesmo tipo de sensor na mesma estufa"""
        cursor = self.connection.cursor()
        
        query = """
        SELECT 
            m.valor_medido,
            m.data_hora_registro
        FROM medicao m
        JOIN sensor s ON m.id_sensor = s.id_sensor
        WHERE s.tipo_sensor = %s
        AND s.id_estufa = %s
        AND m.valor_medido IS NOT NULL
        ORDER BY m.data_hora_registro DESC
        LIMIT %s
        """
        
        cursor.execute(query, (tipo_sensor, id_estufa, limit))
        results = cursor.fetchall()
        cursor.close()
        
        valores = [float(row[0]) for row in results]
        return valores
    
    def calcular_mediana(self, valores):
        """Calcula a mediana de uma lista de valores"""
        if not valores:
            return None
        return statistics.median(valores)
    
    def verificar_anomalia_com_mediana(self, id_medicao):
        """Verifica se uma medição está fora do padrão usando mediana das últimas 5 medições"""
        cursor = self.connection.cursor()
        
        query = """
        SELECT 
            m.id_medicao,
            m.valor_medido,
            m.data_hora_registro,
            s.id_sensor,
            s.tipo_sensor,
            s.unidade_medida,
            s.id_estufa,
            ci.temp_min,
            ci.temp_max,
            ci.umid_min,
            ci.umid_max
        FROM medicao m
        JOIN sensor s ON m.id_sensor = s.id_sensor
        JOIN estufa e ON s.id_estufa = e.id_estufa
        LEFT JOIN lote_plantio lp ON e.id_estufa = lp.id_estufa 
            AND lp.data_previsao_colheita >= CURRENT_DATE
        LEFT JOIN condicao_ideal ci ON lp.id_cultura = ci.id_cultura
        WHERE m.id_medicao = %s
        """
        
        cursor.execute(query, (id_medicao,))
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            return None
        
        valor_atual = float(result[1])
        id_sensor = result[3]
        tipo_sensor = result[4]
        unidade_medida = result[5]
        id_estufa = result[6]
        
        # Pega as últimas 5 medições do mesmo tipo na mesma estufa
        ultimas_medicoes = self.get_ultimas_medicoes_sensor(id_sensor, tipo_sensor, id_estufa, 5)
        
        if len(ultimas_medicoes) < 3:
            print(f"⚠ Poucas medições históricas ({len(ultimas_medicoes)}). Usando valor atual diretamente.")
            valor_para_analise = valor_atual
        else:
            mediana = self.calcular_mediana(ultimas_medicoes)
            print(f"📊 Últimas {len(ultimas_medicoes)} medições: {[f'{v:.2f}' for v in ultimas_medicoes]}")
            print(f"📊 Mediana calculada: {mediana:.2f} {unidade_medida}")
            print(f"📊 Valor atual: {valor_atual:.2f} {unidade_medida}")
            valor_para_analise = mediana
        
        # Verifica se está fora do padrão
        fora_padrao = False
        motivo = ""
        severidade = ""
        
        if tipo_sensor == 'Temperatura' and result[7] is not None:
            temp_min = float(result[7])
            temp_max = float(result[8])
            
            if valor_para_analise < temp_min:
                fora_padrao = True
                diferenca = temp_min - valor_para_analise
                motivo = f"Temperatura abaixo do ideal (mediana: {valor_para_analise:.2f}°C < mínimo: {temp_min}°C)"
                severidade = "Alta" if diferenca > 5 else "Média" if diferenca > 2 else "Baixa"
            elif valor_para_analise > temp_max:
                fora_padrao = True
                diferenca = valor_para_analise - temp_max
                motivo = f"Temperatura acima do ideal (mediana: {valor_para_analise:.2f}°C > máximo: {temp_max}°C)"
                severidade = "Alta" if diferenca > 5 else "Média" if diferenca > 2 else "Baixa"
        
        elif tipo_sensor == 'Umidade' and result[9] is not None:
            umid_min = float(result[9])
            umid_max = float(result[10])
            
            if valor_para_analise < umid_min:
                fora_padrao = True
                diferenca = umid_min - valor_para_analise
                motivo = f"Umidade abaixo do ideal (mediana: {valor_para_analise:.2f}% < mínimo: {umid_min}%)"
                severidade = "Alta" if diferenca > 15 else "Média" if diferenca > 5 else "Baixa"
            elif valor_para_analise > umid_max:
                fora_padrao = True
                diferenca = valor_para_analise - umid_max
                motivo = f"Umidade acima do ideal (mediana: {valor_para_analise:.2f}% > máximo: {umid_max}%)"
                severidade = "Alta" if diferenca > 15 else "Média" if diferenca > 5 else "Baixa"
        
        if fora_padrao:
            return {
                'id_medicao': result[0],
                'valor_atual': valor_atual,
                'valor_mediana': valor_para_analise,
                'ultimas_medicoes': ultimas_medicoes,
                'data_hora': result[2],
                'tipo_sensor': tipo_sensor,
                'unidade_medida': unidade_medida,
                'id_estufa': id_estufa,
                'motivo': motivo,
                'severidade': severidade
            }
        
        return None
    
    def get_estufa_context(self, id_estufa):
        """Obtém informações completas da estufa"""
        cursor = self.connection.cursor()
        query = """
        SELECT id_estufa, nome, localizacao, tamanho, status
        FROM estufa WHERE id_estufa = %s
        """
        cursor.execute(query, (id_estufa,))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return {
                'id_estufa': result[0],
                'nome': result[1],
                'localizacao': result[2],
                'tamanho': result[3],
                'status': result[4]
            }
        return None
    
    def get_atuadores_estufa(self, id_estufa):
        """Obtém todos os atuadores disponíveis na estufa"""
        cursor = self.connection.cursor()
        query = "SELECT id_atuador, tipo_atuador, capacidade FROM atuador WHERE id_estufa = %s"
        cursor.execute(query, (id_estufa,))
        results = cursor.fetchall()
        cursor.close()
        
        return [{'id_atuador': r[0], 'tipo': r[1], 'capacidade': r[2]} for r in results]
    
    def get_cultura_info(self, id_estufa):
        """Obtém informações sobre a cultura plantada na estufa"""
        cursor = self.connection.cursor()
        query = """
        SELECT DISTINCT c.nome_popular, c.nome_cientifico,
               ci.temp_min, ci.temp_max, ci.umid_min, ci.umid_max
        FROM cultura c
        JOIN condicao_ideal ci ON c.id_cultura = ci.id_cultura
        JOIN lote_plantio lp ON c.id_cultura = lp.id_cultura
        WHERE lp.id_estufa = %s AND lp.data_previsao_colheita >= CURRENT_DATE
        ORDER BY lp.data_plantio DESC LIMIT 1
        """
        cursor.execute(query, (id_estufa,))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return {
                'nome_popular': result[0],
                'nome_cientifico': result[1],
                'temp_min': float(result[2]),
                'temp_max': float(result[3]),
                'umid_min': float(result[4]),
                'umid_max': float(result[5])
            }
        return None
    
    def get_funcionario_com_menos_tarefas(self, id_estufa):
        """Seleciona funcionário com menos tarefas pendentes"""
        cursor = self.connection.cursor()
        query = """
        WITH funcionarios_estufa AS (
            SELECT DISTINCT ef.id_funcionario, f.nome
            FROM estufa_funcionario ef
            JOIN funcionario f ON ef.id_funcionario = f.id_funcionario
            WHERE ef.id_estufa = %s AND ef.data_fim IS NULL
        ),
        tarefas_pendentes AS (
            SELECT t.id_funcionario, COUNT(*) as tarefas_pendentes
            FROM tarefa t
            WHERE t.data_conclusao IS NULL
            AND t.id_funcionario IN (SELECT id_funcionario FROM funcionarios_estufa)
            GROUP BY t.id_funcionario
        )
        SELECT fe.id_funcionario, fe.nome, COALESCE(tp.tarefas_pendentes, 0) as tarefas_pendentes
        FROM funcionarios_estufa fe
        LEFT JOIN tarefas_pendentes tp ON fe.id_funcionario = tp.id_funcionario
        ORDER BY COALESCE(tp.tarefas_pendentes, 0) ASC, fe.id_funcionario ASC
        LIMIT 1
        """
        
        cursor.execute(query, (id_estufa,))
        result = cursor.fetchone()
        
        if not result:
            # Fallback
            cursor.execute("""
                SELECT f.id_funcionario, f.nome, COUNT(t.id_tarefa) as tarefas_pendentes
                FROM funcionario f
                LEFT JOIN tarefa t ON f.id_funcionario = t.id_funcionario 
                    AND t.data_conclusao IS NULL
                GROUP BY f.id_funcionario, f.nome
                ORDER BY tarefas_pendentes ASC LIMIT 1
            """)
            result = cursor.fetchone()
        
        cursor.close()
        
        if result:
            return {
                'id_funcionario': result[0],
                'nome': result[1],
                'tarefas_pendentes': result[2]
            }
        return None
    
    def generate_task_with_ai(self, medicao_info, estufa_info, atuadores, cultura_info):
        """Usa IA do Gemini para gerar tarefa contextualizada"""
        if not self.model:
            return f"[{medicao_info['severidade']}] Corrigir {medicao_info['tipo_sensor'].lower()} na {estufa_info['nome']}. {medicao_info['motivo']}"
        
        prompt = f"""Você é um assistente especializado em gestão de estufas inteligentes. 

SITUAÇÃO DETECTADA (CONFIRMADA POR MEDIANA):
- Estufa: {estufa_info['nome']} ({estufa_info['localizacao']})
- Tamanho: {estufa_info['tamanho']} m²
- Problema: {medicao_info['motivo']}
- Severidade: {medicao_info['severidade']}
- Tipo de sensor: {medicao_info['tipo_sensor']}
- Valor atual: {medicao_info['valor_atual']} {medicao_info['unidade_medida']}
- Mediana (últimas 5 medições): {medicao_info['valor_mediana']:.2f} {medicao_info['unidade_medida']}
- Histórico recente: {[f"{v:.2f}" for v in medicao_info['ultimas_medicoes']]}

CULTURA ATUAL:
"""
        if cultura_info:
            prompt += f"""- Nome: {cultura_info['nome_popular']} ({cultura_info['nome_cientifico']})
- Temperatura ideal: {cultura_info['temp_min']}°C - {cultura_info['temp_max']}°C
- Umidade ideal: {cultura_info['umid_min']}% - {cultura_info['umid_max']}%
"""
        else:
            prompt += "- Nenhuma cultura cadastrada atualmente\n"
        
        prompt += "\nATUADORES DISPONÍVEIS NA ESTUFA:\n"
        for atuador in atuadores:
            prompt += f"- {atuador['tipo']} (Capacidade: {atuador['capacidade']})\n"
        
        prompt += """
TAREFA:
Gere uma descrição CONCISA e TÉCNICA (máximo 400 caracteres) para uma tarefa de correção urgente.
A descrição deve:
1. Especificar qual atuador usar (se aplicável)
2. Explicar BREVEMENTE a ação necessária
3. Mencionar a severidade e tendência
4. Ser direta e objetiva

RETORNE APENAS A DESCRIÇÃO DA TAREFA, SEM INTRODUÇÕES.
"""
        
        try:
            response = self.model.generate_content(prompt)
            descricao = response.text.strip()
            if len(descricao) > 400:
                descricao = descricao[:397] + "..."
            return descricao
        except Exception as e:
            print(f"Erro ao gerar tarefa com IA: {e}")
            return f"[{medicao_info['severidade']}] Corrigir {medicao_info['tipo_sensor'].lower()} na {estufa_info['nome']}. {medicao_info['motivo']}"
    
    def create_task_in_database(self, descricao, id_estufa, severidade="Média"):
        """Cria tarefa no banco com distribuição igualitária"""
        cursor = self.connection.cursor()
        
        funcionario_info = self.get_funcionario_com_menos_tarefas(id_estufa)
        
        if not funcionario_info:
            print("❌ Erro: Nenhum funcionário disponível!")
            cursor.close()
            return None
        
        print(f"👤 Tarefa atribuída a: {funcionario_info['nome']} "
              f"(Tarefas pendentes: {funcionario_info['tarefas_pendentes']})")
        
        # Define urgência
        horas = 0.5 if severidade == "Alta" else 1 if severidade == "Média" else 2
        data_agendada = datetime.now() + timedelta(hours=horas)
        
        query = """
        INSERT INTO tarefa (descricao, data_conclusao, data_agendada, id_funcionario)
        VALUES (%s, NULL, %s, %s) RETURNING id_tarefa
        """
        
        cursor.execute(query, (descricao, data_agendada, funcionario_info['id_funcionario']))
        id_tarefa = cursor.fetchone()[0]
        self.connection.commit()
        cursor.close()
        
        return id_tarefa
    
    def process_medicao_automatico(self, id_medicao):
        """Processo automático completo após inserção de medição"""
        print(f"\n🔍 Analisando medição ID: {id_medicao}...")
        
        medicao_info = self.verificar_anomalia_com_mediana(id_medicao)
        
        if not medicao_info:
            print("✅ Medição dentro do padrão esperado (baseado na mediana).")
            return None
        
        print(f"\n⚠️  ANOMALIA CONFIRMADA [{medicao_info['severidade']}]: {medicao_info['motivo']}")
        
        estufa_info = self.get_estufa_context(medicao_info['id_estufa'])
        atuadores = self.get_atuadores_estufa(medicao_info['id_estufa'])
        cultura_info = self.get_cultura_info(medicao_info['id_estufa'])
        
        print("🤖 Consultando IA para gerar tarefa corretiva...")
        descricao_tarefa = self.generate_task_with_ai(medicao_info, estufa_info, atuadores, cultura_info)
        
        print(f"📝 Tarefa gerada: {descricao_tarefa}")
        
        id_tarefa = self.create_task_in_database(descricao_tarefa, medicao_info['id_estufa'], medicao_info['severidade'])
        
        if id_tarefa:
            print(f"✅ Tarefa #{id_tarefa} criada com sucesso!")
            print(f"⏰ Urgência: {medicao_info['severidade']}")
        
        return id_tarefa


# Função para ser chamada do sistema principal
def inserir_medicao_com_analise_ia(connect, id_sensor, valor_medido):
    """
    Insere medição e faz análise automática com IA
    ESTA É A FUNÇÃO PRINCIPAL PARA CHAMAR DO MENU
    """
    cursor = connect.cursor()
    
    try:
        # Insere a medição
        query = """
        INSERT INTO medicao (data_hora_registro, valor_medido, id_sensor)
        VALUES (NOW(), %s, %s)
        RETURNING id_medicao
        """
        
        cursor.execute(query, (valor_medido, id_sensor))
        id_medicao = cursor.fetchone()[0]
        connect.commit()
        cursor.close()
        
        print(f"✅ Medição #{id_medicao} inserida no banco de dados")
        
        # Processa automaticamente com IA
        monitor = AIGreenhouseMonitor(connect)
        monitor.process_medicao_automatico(id_medicao)
        
        return id_medicao
        
    except Exception as e:
        print(f"❌ Erro ao inserir medição: {e}")
        connect.rollback()
        cursor.close()
        return None