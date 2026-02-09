# processador_corrigido_final.py
import pandas as pd
import re
from datetime import datetime

CONTAS_PROVISAO = {
    '160': 'Salários a Pagar',
    '163': '13º Salário a Pagar',
    '169': 'Pro-labore a Pagar',
    '172': 'FGTS a Pagar',
    '196': 'COFINS a Pagar',
    '197': 'PIS a Pagar',
    '642': 'Contribuição Assistencial a Pagar',
    '708': 'DARF Previdenciário a Pagar'
}

PALAVRAS_AJUSTE = [
    'ajuste',
    'correção',
    'compensação',
    'reversão',
    'provisão a menor'
]

def converter_valor(valor):
    """Converte qualquer formato para float"""
    if pd.isna(valor):
        return 0.0

    # Se já é número
    if isinstance(valor, (int, float)):
        return float(valor)

    # Se é string
    texto = str(valor).strip()
    if texto == '':
        return 0.0

    # Remover "Saldo anterior:" se houver
    texto = texto.replace('Saldo anterior:', '').strip()

    # Remover R$ e espaços
    texto = texto.replace('R$', '').replace('$', '').strip()

    # Tentar converter direto
    try:
        return float(texto)
    except:
        pass

    # Formato brasileiro: 2.323,13 (mas já vem como 2323.13)
    texto = texto.replace('.', '').replace(',', '.')

    try:
        return float(texto)
    except:
        return 0.0

def extrair_saldo_anterior_corrigido(row):
    """
    CORREÇÃO: Verifica se a coluna D tem "Saldo anterior:"
    e pega o valor da coluna F
    """
    # Verificar se temos coluna D (índice 3)
    if len(row) <= 3:
        return 0.0

    col_d = row.iloc[3]
    if pd.isna(col_d):
        return 0.0

    # Verificar se coluna D tem "Saldo anterior:"
    if isinstance(col_d, str) and 'saldo anterior:' in col_d.lower():
        # Agora pegar o valor da coluna F (índice 5)
        if len(row) > 5:
            col_f = row.iloc[5]
            if not pd.isna(col_f):
                return converter_valor(col_f)

    return 0.0

def extrair_data_texto(texto):
    if not texto:
        return ''
    texto = str(texto)
    match = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
    if match:
        return match.group(1)
    match = re.search(r'(?<!\d)(\d{2}/\d{4})(?!\d)', texto)
    if match:
        return match.group(1)
    return ''

def is_cabecalho_conta(texto):
    """Verifica se é cabeçalho de conta"""
    if pd.isna(texto):
        return False, None, None

    texto_str = str(texto).strip()
    match = re.match(r'^(\d{2,5})\s*-\s*(.+)$', texto_str)

    if match:
        conta_numero = match.group(1)
        if conta_numero in CONTAS_PROVISAO:
            return True, conta_numero, match.group(2)

    return False, None, None

def processar_passivo_corrigido(df, competencia_inicial=None):
    """Versão final corrigida"""
    print("=" * 100)
    print("PROCESSADOR FINAL CORRIGIDO")
    print("=" * 100)

    provisoes = {}
    conta_atual = None
    nome_conta_atual = None
    data_atual = None

    def competencia_aaaamm(dt):
        return dt.strftime('%Y%m')

    def competencia_anterior(aaaamm):
        if not aaaamm or len(aaaamm) != 6:
            return None
        ano = int(aaaamm[:4])
        mes = int(aaaamm[4:6])
        if mes == 1:
            ano -= 1
            mes = 12
        else:
            mes -= 1
        return f"{ano}{mes:02d}"

    for idx, row in df.iterrows():
        historico = str(row.iloc[0]) if len(row) > 0 and not pd.isna(row.iloc[0]) else ''
        debito = converter_valor(row.iloc[3]) if len(row) > 3 else 0.0
        credito = converter_valor(row.iloc[4]) if len(row) > 4 else 0.0

        # DEBUG para conta 708 (desativado para evitar problemas de encoding)
        debug_708 = False

        if debug_708:
            print("\n" + "-" * 60)
            print(f"LINHA {idx}:")
            print(f"  Histórico: '{historico[:60]}'")
            print(f"  Débito: {debito}, Crédito: {credito}")
            print(f"  Conta atual: {conta_atual}")

        # 1. Verificar DATA
        data_match = re.search(r'(\d{4}-\d{2}-\d{2})', historico)
        if data_match:
            try:
                data_atual = datetime.strptime(data_match.group(1), '%Y-%m-%d')
                data_str = data_atual.strftime('%d/%m/%Y') if data_atual else ''
                if not data_str:
                    data_str = extrair_data_texto(historico)
                chave_doc = row.iloc[1] if len(row) > 1 else ''
                contra = row.iloc[2] if len(row) > 2 else ''
                if debug_708:
                    print(f"  → 📅 Data: {data_atual.strftime('%d/%m/%Y')}")
                continue
            except:
                pass

        data_match = re.search(r'(\d{2}/\d{2}/\d{4})', historico)
        if data_match:
            try:
                data_atual = datetime.strptime(data_match.group(1), '%d/%m/%Y')
                if debug_708:
                    print(f"  → 📅 Data: {data_atual.strftime('%d/%m/%Y')}")
                continue
            except:
                pass

        # 2. Verificar CABEÇALHO DE CONTA
        is_cabecalho, conta_numero, nome_conta = is_cabecalho_conta(historico)

        if is_cabecalho:
            conta_atual = conta_numero
            nome_conta_atual = nome_conta

            data_str = data_atual.strftime('%d/%m/%Y') if data_atual else ''
            if not data_str:
                data_str = extrair_data_texto(historico)
            chave_doc = row.iloc[1] if len(row) > 1 else ''
            contra = row.iloc[2] if len(row) > 2 else ''
            if debug_708:
                print(f"  → 📋 Cabeçalho: {conta_atual} - {nome_conta}")

            # EXTRAIR SALDO ANTERIOR (CORREÇÃO AQUI!)
            saldo_anterior = extrair_saldo_anterior_corrigido(row)

            if saldo_anterior > 0:
                if debug_708:
                    print(f"  → 💰 SALDO ANTERIOR ENCONTRADO: R$ {saldo_anterior:.2f}")

                # Criar competência
                competencia = competencia_anterior(competencia_inicial)
                if not competencia:
                    continue
                chave = (conta_atual, competencia)

                if chave not in provisoes:
                    provisoes[chave] = {
                        'conta': conta_atual,
                        'nome_conta': CONTAS_PROVISAO[conta_atual],
                        'competencia': competencia,
                        'creditos': 0.0,
                        'ajustes': 0.0,
                        'lancamentos': []
                    }

                # Adicionar saldo anterior
                provisoes[chave]['creditos'] += saldo_anterior
                provisoes[chave]['lancamentos'].append({
                    'data': '',
                    'historico': f"Saldo anterior - {nome_conta}",
                    'chave': '',
                    'contra': '',
                    'tipo': 'Credito (Saldo Anterior)',
                    'valor': saldo_anterior
                })
            elif debug_708:
                print(f"  → ⚠️  Nenhum saldo anterior encontrado")

            continue

        # 3. Se não tem conta atual, pular
        if not conta_atual:
            if debug_708:
                print(f"  → ⏭️  PULANDO (sem conta atual)")
            continue

        # 4. Se conta não está mapeada, pular
        if conta_atual not in CONTAS_PROVISAO:
            if debug_708:
                print(f"  → ⏭️  PULANDO (conta {conta_atual} não mapeada)")
            continue

        # 5. Pular linhas vazias
        if historico == '' and debito == 0 and credito == 0:
            if debug_708:
                print(f"  → ⏭️  PULANDO (linha vazia)")
            continue

        # 6/7. Criar/obter provisão
        competencia = competencia_aaaamm(data_atual) if data_atual else competencia_inicial
        if not competencia:
            if debug_708:
                print(f"  → ⏭️  PULANDO (sem competência)")
            continue
        chave = (conta_atual, competencia)

        if chave not in provisoes:
            provisoes[chave] = {
                'conta': conta_atual,
                'nome_conta': CONTAS_PROVISAO[conta_atual],
                'competencia': competencia,
                'creditos': 0.0,
                'ajustes': 0.0,
                'lancamentos': []
            }

        # 8. Processar CRÉDITOS
        if credito > 0:
            data_str = data_atual.strftime('%d/%m/%Y') if data_atual else ''
            if not data_str:
                data_str = extrair_data_texto(historico)
            chave_doc = row.iloc[1] if len(row) > 1 else ''
            contra = row.iloc[2] if len(row) > 2 else ''
            provisoes[chave]['creditos'] += credito
            provisoes[chave]['lancamentos'].append({
                'data': data_str,
                'historico': historico,
                'chave': '' if pd.isna(chave_doc) else str(chave_doc),
                'contra': '' if pd.isna(contra) else str(contra),
                'tipo': 'Credito',
                'valor': credito
            })
            if debug_708:
                print(f"  → 💚 Crédito adicionado: R$ {credito:.2f}")

        # 9. Processar DÉBITOS (apenas ajustes)
        elif debito > 0:
            historico_lower = historico.lower()
            if any(palavra in historico_lower for palavra in PALAVRAS_AJUSTE):
                data_str = data_atual.strftime('%d/%m/%Y') if data_atual else ''
                if not data_str:
                    data_str = extrair_data_texto(historico)
                chave_doc = row.iloc[1] if len(row) > 1 else ''
                contra = row.iloc[2] if len(row) > 2 else ''
                provisoes[chave]['ajustes'] += debito
                provisoes[chave]['lancamentos'].append({
                    'data': data_str,
                    'historico': historico,
                    'chave': '' if pd.isna(chave_doc) else str(chave_doc),
                    'contra': '' if pd.isna(contra) else str(contra),
                    'tipo': 'Debito (Ajuste)',
                    'valor': debito
                })
                if debug_708:
                    print(f"  → 🔴 Ajuste adicionado: R$ {debito:.2f}")

    return provisoes

def main():
    """Teste principal"""
    print("=" * 100)
    print("TESTE FINAL - SALDO ANTERIOR DA CONTA 708")
    print("=" * 100)

    # Carregar arquivo
    try:
        df = pd.read_excel('Passivo.xlsx', sheet_name='Passivo')
        print("✓ Arquivo carregado")
    except Exception as e:
        print(f"✗ Erro: {e}")
        return

    # Processar
    provisoes = processar_passivo_corrigido(df)

    # Resultados específicos da conta 708
    print(f"\n{'='*100}")
    print("RESULTADO ESPECÍFICO DA CONTA 708")
    print(f"{'='*100}")

    # Procurar conta 708
    conta_708_encontrada = False

    for chave, info in provisoes.items():
        if info['conta'] == '708':
            conta_708_encontrada = True

            saldo = info['creditos'] - info['ajustes']

            print(f"\n✅ CONTA 708 - {info['nome_conta']}")
            print(f"   Competência: {info['competencia']}")
            print(f"   Créditos totais: R$ {info['creditos']:,.2f}")
            print(f"   Ajustes: R$ {info['ajustes']:,.2f}")
            print(f"   Saldo final: R$ {saldo:,.2f}")

            print(f"\n   📋 Lançamentos ({len(info['lancamentos'])}):")

            # Separar saldo anterior dos outros lançamentos
            saldo_anterior = 0
            outros_lancamentos = []

            for lanc in info['lancamentos']:
                if 'Saldo anterior' in lanc['tipo']:
                    saldo_anterior = lanc['valor']
                    print(f"   💰 SALDO ANTERIOR: R$ {saldo_anterior:,.2f}")
                else:
                    outros_lancamentos.append(lanc)

            if outros_lancamentos:
                print(f"\n   Outros lançamentos:")
                for lanc in outros_lancamentos:
                    print(f"   - {lanc['data']} | {lanc['tipo']} | R$ {lanc['valor']:,.2f}")
                    if lanc['descricao']:
                        desc = lanc['descricao'][:50] + "..." if len(lanc['descricao']) > 50 else lanc['descricao']
                        print(f"      {desc}")

            # Verificar cálculo
            total_lancamentos = sum(lanc['valor'] for lanc in outros_lancamentos if lanc['tipo'] == 'Crédito')
            total_esperado = saldo_anterior + total_lancamentos

            print(f"\n   🧮 VERIFICAÇÃO:")
            print(f"   Saldo anterior: R$ {saldo_anterior:,.2f}")
            print(f"   + Lançamentos do mês: R$ {total_lancamentos:,.2f}")
            print(f"   = Total esperado: R$ {total_esperado:,.2f}")
            print(f"   Total encontrado: R$ {info['creditos']:,.2f}")

            if abs(info['creditos'] - total_esperado) < 0.01:
                print(f"   ✅ Cálculo correto!")
            else:
                print(f"   ❌ Diferença: R$ {abs(info['creditos'] - total_esperado):.2f}")

    if not conta_708_encontrada:
        print("❌ Conta 708 não encontrada!")

# Para compatibilidade com app.py
def processar_razao_passivo(df, competencia_inicial=None):
    return processar_passivo_corrigido(df, competencia_inicial)

if __name__ == "__main__":
    main()
