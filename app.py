# app.py - VERSÃO OTIMIZADA E CONFIÁVEL
import streamlit as st
import base64
import pandas as pd
import re
import unicodedata
import io
from datetime import datetime, timedelta
from pathlib import Path
from processador import processar_razao_passivo
from regras import MAPA_CONTAS_BANCO, CONTAS_FOLHA

# ======================================================
# CONFIGURAÇÃO
# ======================================================
logo_path = Path(__file__).resolve().parent / "Logo_transparente.png"
st.set_page_config(
    page_title="Conciliador PRO",
    layout="wide",
    page_icon=str(logo_path)
)

# Tema dark com alto contraste
st.markdown(
    """
    <style>
    :root {
        --bg: #0b0f14;
        --panel: #101722;
        --panel-2: #0e151f;
        --text: #f8fafc;
        --muted: #cbd5e1;
        --accent: #60a5fa;
        --accent-2: #22c55e;
        --danger: #f87171;
        --border: #334155;
    }

    .stApp {
        background: radial-gradient(1200px 800px at 10% -10%, #1a2433 0%, var(--bg) 55%);
        color: var(--text);
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown, .stCaption, .stMetric,
    .stTextInput label, .stSelectbox label, .stCheckbox label {
        color: var(--text) !important;
    }

    .stCaption, .stMarkdown p, .stTextInput label,
    .stSelectbox label, .stCheckbox label {
        color: var(--muted) !important;
    }

    .stTextInput>div>div>input, .stSelectbox>div>div>div>div, .stTextArea textarea {
        background: #0f1622 !important;
        color: var(--text) !important;
        border: 1px solid #475569 !important;
        border-radius: 10px !important;
    }

    /* Selectbox input background */
    div[data-baseweb="select"] > div {
        background: #0f1622 !important;
        color: var(--text) !important;
        border: 1px solid #475569 !important;
    }
    div[data-baseweb="select"] input {
        color: var(--text) !important;
    }

    /* Checkbox label */
    .stCheckbox label span {
        color: var(--text) !important;
    }

    .stFileUploader, .stFileUploader * {
        color: var(--text) !important;
    }
    .stFileUploader section {
        background: #0f1622 !important;
        border: 1px solid #475569 !important;
        border-radius: 12px !important;
    }
    .stFileUploader button {
        background: #1f2937 !important;
        color: var(--text) !important;
        border: 1px solid #334155 !important;
    }

    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;
        color: white !important;
        border: 1px solid #1f2937 !important;
        border-radius: 10px !important;
        box-shadow: 0 6px 18px rgba(96,165,250,0.35);
    }

    .stDownloadButton>button {
        background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%) !important;
        color: white !important;
        border: 1px solid #1f2937 !important;
        border-radius: 10px !important;
        box-shadow: 0 6px 18px rgba(14,165,233,0.35);
    }

    div[data-testid="stMetric"] {
        background: #0b1220 !important;
        border: 1px solid #3b4a63 !important;
        border-radius: 12px !important;
        padding: 12px !important;
    }
    div[data-testid="stMetric"] * {
        color: #f1f5f9 !important;
    }

    /* Resultado conciliação cards claros -> texto escuro para contraste */
    .stMarkdown div[style*="background: #f0fdf4"],
    .stMarkdown div[style*="background: #fef2f2"] {
        color: #0f172a !important;
    }
    .stMarkdown div[style*="background: #f0fdf4"] strong,
    .stMarkdown div[style*="background: #fef2f2"] strong,
    .stMarkdown div[style*="background: #f0fdf4"] small,
    .stMarkdown div[style*="background: #fef2f2"] small {
        color: #0f172a !important;
    }

    /* Cards de créditos/ajustes claros -> dark */
    .stMarkdown div[style*="background: #dbeafe"],
    .stMarkdown div[style*="background: #fef3c7"] {
        background: #0f1622 !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
    }
    .stMarkdown div[style*="background: #dbeafe"] div,
    .stMarkdown div[style*="background: #fef3c7"] div {
        color: #f8fafc !important;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #475569 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    hr {
        border-color: #334155 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ======================================================
# ESTADO DA APLICAÇÃO
# ======================================================
if 'etapa' not in st.session_state:
    st.session_state.etapa = 1

def tem_provisoes():
    return ('provisoes' in st.session_state and
            st.session_state.provisoes is not None and
            len(st.session_state.provisoes) > 0)

def tem_ofx():
    return ('transacoes_ofx' in st.session_state and
            st.session_state.transacoes_ofx is not None and
            not st.session_state.transacoes_ofx.empty)

def extrair_competencia_inicial(df):
    coluna_hist = 'Histórico' if 'Histórico' in df.columns else df.columns[0]
    for valor in df[coluna_hist].tolist():
        if pd.isna(valor):
            continue
        texto = str(valor)
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto)
        if match:
            return f"{match.group(1)}{match.group(2)}"
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto)
        if match:
            return f"{match.group(3)}{match.group(2)}"
        match = re.search(r'(?<!\d)(\d{2})/(\d{4})(?!\d)', texto)
        if match:
            return f"{match.group(2)}{match.group(1)}"
    return None

# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================
def parse_ofx_date(texto):
    if not texto:
        return None
    match = re.search(r'(\d{8})', texto)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), '%Y%m%d')
    except Exception:
        return None

def ler_ofx(arquivo):
    conteudo = arquivo.read()
    if isinstance(conteudo, bytes):
        texto = conteudo.decode(errors='ignore')
    else:
        texto = str(conteudo)

    blocos = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', texto, flags=re.IGNORECASE | re.DOTALL)
    registros = []

    for bloco in blocos:
        dt = re.search(r'<DTPOSTED>([^<]+)', bloco, flags=re.IGNORECASE)
        amt = re.search(r'<TRNAMT>([^<]+)', bloco, flags=re.IGNORECASE)
        memo = re.search(r'<MEMO>([^<]+)', bloco, flags=re.IGNORECASE)
        name = re.search(r'<NAME>([^<]+)', bloco, flags=re.IGNORECASE)

        data = parse_ofx_date(dt.group(1)) if dt else None
        valor_txt = amt.group(1).replace(',', '.') if amt else '0'
        try:
            valor = float(valor_txt)
        except Exception:
            valor = 0.0

        descricao = (memo.group(1) if memo else '') or (name.group(1) if name else '')
        descricao = str(descricao).strip()

        registros.append({'data': data, 'descricao': descricao, 'valor': valor})

    return pd.DataFrame(registros)

def normalizar_nome(texto):
    if texto is None:
        return ''
    texto = str(texto).upper()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\b(DE|DA|DO|DOS|DAS)\b', ' ', texto)
    texto = re.sub(r'[^A-Z\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def extrair_nome_folha(historico):
    texto = str(historico or '').strip()
    if ' - ' in texto:
        return texto.split(' - ')[-1].strip()
    return texto

def extrair_nome_ofx(descricao):
    texto = str(descricao or '').strip()
    texto_upper = texto.upper()
    if 'PAGAMENTO PIX' in texto_upper:
        pos = texto_upper.rfind('PAGAMENTO PIX')
        texto = texto[pos + len('PAGAMENTO PIX'):].strip()
    palavras = re.findall(r'[A-Za-zÀ-ÿ]+', texto)
    if palavras:
        return ' '.join(palavras[-4:])
    return texto

def token_overlap(a, b):
    ta = [t for t in a.split(' ') if t]
    tb = [t for t in b.split(' ') if t]
    if not ta or not tb:
        return 0.0
    inter = set(ta).intersection(set(tb))
    return len(inter) / max(len(ta), len(tb))

def nome_match(nome_a, nome_b):
    if not nome_a or not nome_b:
        return False
    if nome_a in nome_b or nome_b in nome_a:
        return True
    return token_overlap(nome_a, nome_b) >= 0.7

def competencia_range(competencia, dias_pos=60):
    try:
        ano = int(competencia[:4])
        mes = int(competencia[4:6])
        inicio = datetime(ano, mes, 1)
        if mes == 12:
            prox = datetime(ano + 1, 1, 1)
        else:
            prox = datetime(ano, mes + 1, 1)
        fim_mes = prox - timedelta(days=1)
        fim = fim_mes + timedelta(days=dias_pos)
        return inicio, fim
    except Exception:
        return None, None

def normalizar_coluna(nome):
    texto = str(nome).strip().lower()
    texto = re.sub(r'[^a-z0-9]+', '', texto)
    return texto

def ler_csv(arquivo):
    try:
        df = pd.read_csv(arquivo, sep=None, engine='python')
    except Exception:
        arquivo.seek(0)
        df = pd.read_csv(arquivo, sep=';')

    colunas = {c: normalizar_coluna(c) for c in df.columns}
    df = df.rename(columns=colunas)

    col_data = 'data' if 'data' in df.columns else None
    col_desc = None
    for c in ['descricao', 'historico', 'hist', 'memo', 'name']:
        if c in df.columns:
            col_desc = c
            break

    col_valor = None
    for c in ['valor', 'vlr', 'amount', 'valorlancamento']:
        if c in df.columns:
            col_valor = c
            break

    if col_data:
        df['data'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
    else:
        df['data'] = pd.NaT

    if col_desc:
        df['descricao'] = df[col_desc].astype(str)
    else:
        df['descricao'] = ''

    if col_valor:
        df['valor'] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0.0)
    else:
        df['valor'] = 0.0

    return df[['data', 'descricao', 'valor']]

def filtrar_pagamentos(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=['data', 'descricao', 'valor', 'tipo'])
    df = df.copy()
    df = df[df['valor'] < 0]
    df['valor'] = df['valor'].abs()
    df['tipo'] = 'Pagamento'
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df.dropna(subset=['data'])
    return df

def format_valor_sci(v):
    try:
        return f"{float(v):.2f}"
    except Exception:
        return "0.00"

def gerar_linha_sci(linha_num, data_yyyymmdd, conta_debito, conta_credito, valor, cod_hist, complemento, documento="", participante_debito=""):
    campos = [
        str(linha_num),
        data_yyyymmdd,
        str(conta_debito),
        str(conta_credito),
        format_valor_sci(valor),
        str(cod_hist),
        complemento,
        documento
    ]
    while len(campos) < 14:
        campos.append('')
    linha = ",".join(campos)
    if participante_debito:
        linha = f"{linha},{participante_debito}"
    return linha

def exportar_txt_sci_pagamentos(df_conciliados, conta_banco="5", cod_hist="1001", gerar_encargos=False, conta_encargos=None):
    linhas = []
    linha_num = 1
    for _, row in df_conciliados.iterrows():
        data_pagto = str(row.get('data_pagto', '') or '')
        competencia = str(row.get('competencia', '') or '')
        descricao_ofx = str(row.get('descricao_ofx', '') or row.get('descricao', '') or '')
        nome_conta = str(row.get('nome_conta', '') or '')
        conta_provisao = str(row.get('conta_provisao', '') or '')
        valor_pago = float(row.get('valor_pago', 0) or 0)

        if valor_pago <= 0 or not conta_provisao:
            continue

        if data_pagto and '/' in data_pagto:
            try:
                data_yyyymmdd = datetime.strptime(data_pagto, '%d/%m/%Y').strftime('%Y%m%d')
            except Exception:
                data_yyyymmdd = ''
        elif len(data_pagto) == 8 and data_pagto.isdigit():
            data_yyyymmdd = data_pagto
        else:
            data_yyyymmdd = f"{competencia}01" if len(competencia) == 6 else ''

        nome_ref = nome_conta if nome_conta else conta_provisao
        complemento = f"Pgto {nome_ref} {competencia} - {descricao_ofx}".strip()[:200]

        linhas.append(
            gerar_linha_sci(
                linha_num,
                data_yyyymmdd,
                conta_provisao,
                conta_banco,
                valor_pago,
                cod_hist,
                complemento,
                "OFX",
                ""
            )
        )
        linha_num += 1

    return "\n".join(linhas)

def buscar_correspondencias(provisoes, transacoes_ofx):
    """Busca valores correspondentes no extrato"""
    resultados = []

    pagamentos = transacoes_ofx[transacoes_ofx['valor'] < 0].copy()
    pagamentos['valor_abs'] = pagamentos['valor'].abs()
    pagamentos['descricao'] = pagamentos['descricao'].astype(str)
    pagamentos['nome_norm'] = pagamentos['descricao'].apply(lambda d: normalizar_nome(extrair_nome_ofx(d)))
    pagamentos['data'] = pd.to_datetime(pagamentos['data'], errors='coerce')
    usados_ofx = set()

    def tem_exclusao_forte(descricao):
        texto = str(descricao or '').upper()
        return any(p in texto for p in [
            'CONTABIL', 'CONTABILIDADE', 'CEF', 'MATRIZ', 'CDD', 'IPATINGA',
            'FORNECEDOR', 'ALUGUEL', 'BOLETO', 'DARF', 'FGTS', 'IMPOSTO',
            'RECEITA', 'RFB', 'TESOURO'
        ])

    def tokens_pendentes(pendentes):
        tokens = set()
        for item in pendentes:
            nome = item.get('nome_func', '') or ''
            nome_norm = normalizar_nome(nome)
            for t in nome_norm.split(' '):
                if len(t) >= 3:
                    tokens.add(t)
        return tokens

    def eh_provavel_folha_categoria(descricao, conta, tokens_nome):
        texto = str(descricao or '').upper()
        if tem_exclusao_forte(texto):
            return False
        if str(conta) == '169':
            inclui = any(p in texto for p in ['PROLAB', 'PRO-LAB', 'SOCIO', 'RETIRADA'])
        else:
            inclui = any(p in texto for p in [
                'SAL', 'SALAR', 'FOLHA', 'LIQ', 'PAGTO SAL', 'PAGAMENTO SAL',
                'PIX SICREDI-'
            ])
        if str(conta) == '169':
            # Para pro-labore, exige nome do socio (tokens) no historico
            for t in tokens_nome:
                if t in texto:
                    return True
            return False
        if inclui:
            return True
        for t in tokens_nome:
            if t in texto:
                return True
        return False

    for (conta, competencia), dados in provisoes.items():
        valor_provisao = dados['creditos'] - dados['ajustes']

        if str(conta) in CONTAS_FOLHA:
            itens_folha = []
            for lanc in dados.get('lancamentos', []):
                historico = lanc.get('historico', '')
                tipo = str(lanc.get('tipo', '') or '').lower()
                nome_func = extrair_nome_folha(historico)
                valor_item = float(lanc.get('valor', 0) or 0)
                if valor_item <= 0 or 'debito' in tipo:
                    continue
                itens_folha.append({
                    'competencia': competencia,
                    'conta_provisao': conta,
                    'nome_func': nome_func,
                    'nome_norm': normalizar_nome(nome_func),
                    'valor': valor_item,
                    'historico': historico,
                    'chave': lanc.get('chave', ''),
                    'contra': lanc.get('contra', '')
                })

            transacoes_encontradas = []
            conciliados_func = []
            pendentes_func = []
            total_conciliado = 0.0
            inicio, fim = competencia_range(competencia, dias_pos=60)

            for item in itens_folha:
                if not item['nome_norm']:
                    pendentes_func.append({
                        'nome_func': '(Sem nome)',
                        'valor': item['valor']
                    })
                    continue
                match_idx = None
                for idx, pay in pagamentos.iterrows():
                    if idx in usados_ofx:
                        continue
                    if abs(pay['valor_abs'] - item['valor']) > 0.01:
                        continue
                    if inicio and fim:
                        if pd.isna(pay['data']) or not (inicio <= pay['data'] <= fim):
                            continue
                    if not nome_match(item['nome_norm'], pay['nome_norm']):
                        continue
                    match_idx = idx
                    break

                if match_idx is not None:
                    pay = pagamentos.loc[match_idx]
                    usados_ofx.add(match_idx)
                    data_match = pay['data']
                    if hasattr(data_match, 'strftime'):
                        data_fmt = data_match.strftime('%d/%m/%Y')
                    else:
                        data_fmt = str(data_match)
                    transacoes_encontradas.append({
                        'data': data_fmt,
                        'descricao': pay['descricao'],
                        'valor': pay['valor_abs'],
                        'nome_func': item['nome_func'],
                        'tipo': 'funcionario',
                        'chave': ''
                    })
                    conciliados_func.append({
                        'nome_func': item['nome_func'],
                        'valor': item['valor'],
                        'data': data_fmt,
                        'descricao_ofx': pay['descricao']
                    })
                    total_conciliado += item['valor']
                else:
                    pendentes_func.append({
                        'nome_func': item['nome_func'],
                        'valor': item['valor']
                    })

            total_itens = sum(i['valor'] for i in itens_folha)
            total_pendente = max(total_itens - total_conciliado, 0.0)
            status_total = 'PENDENTE'
            if total_pendente > 0:
                inicio_total, fim_total = competencia_range(competencia, dias_pos=10)
                tokens_nome = tokens_pendentes(pendentes_func)
                nomes_pendentes_norm = [
                    normalizar_nome(p.get('nome_func', '') or '')
                    for p in pendentes_func
                    if p.get('nome_func')
                ]
                candidatos_idx = []
                for idx, pay in pagamentos.iterrows():
                    if idx in usados_ofx:
                        continue
                    if inicio_total and fim_total:
                        if pd.isna(pay['data']) or not (inicio_total <= pay['data'] <= fim_total):
                            continue
                    if tem_exclusao_forte(pay['descricao']):
                        continue
                    if str(conta) == '169':
                        if not nomes_pendentes_norm:
                            continue
                        if not any(nome_match(n, pay['nome_norm']) for n in nomes_pendentes_norm):
                            continue
                    else:
                        if not eh_provavel_folha_categoria(pay['descricao'], conta, tokens_nome):
                            continue
                    if pay['valor_abs'] > (1.5 * total_pendente):
                        continue
                    candidatos_idx.append(idx)

                candidatos = pagamentos.loc[candidatos_idx].sort_values('data')
                soma_candidatos = candidatos['valor_abs'].sum() if not candidatos.empty else 0.0
                if soma_candidatos > 0:
                    acumulado = 0.0
                    for idx, pay in candidatos.iterrows():
                        if acumulado >= total_pendente:
                            break
                        usados_ofx.add(idx)
                        data_match = pay['data']
                        if hasattr(data_match, 'strftime'):
                            data_fmt = data_match.strftime('%d/%m/%Y')
                        else:
                            data_fmt = str(data_match)
                        transacoes_encontradas.append({
                            'data': data_fmt,
                            'descricao': pay['descricao'],
                            'valor': pay['valor_abs'],
                            'nome_func': '',
                            'tipo': 'total',
                            'chave': ''
                        })
                        acumulado += pay['valor_abs']

            total_pago_banco = sum(t['valor'] for t in transacoes_encontradas)
            total_pendente_final = max(total_itens - total_pago_banco, 0.0)
            if total_pendente_final <= 0.01 and not pendentes_func:
                status_total = 'QUITADO'
            elif total_pago_banco > 0:
                status_total = 'PARCIAL'
            else:
                status_total = 'PENDENTE'

            resultados.append({
                'conta': conta,
                'nome_conta': dados['nome_conta'],
                'competencia': competencia,
                'valor_provisao': total_itens,
                'encontrado': len(transacoes_encontradas) > 0,
                'transacoes': transacoes_encontradas,
                'folha': True,
                'lancamentos_razao': dados.get('lancamentos', []),
                'conciliados_func': conciliados_func,
                'pendentes_func': pendentes_func,
                'total_provisao': total_itens,
                'total_pago': total_pago_banco,
                'total_pendente': total_pendente_final,
                'status_total': status_total
            })
            continue

        matches = pagamentos[abs(pagamentos['valor_abs'] - valor_provisao) < 0.01]

        if not matches.empty:
            transacoes_encontradas = []
            for _, match in matches.iterrows():
                data_match = match['data']
                if hasattr(data_match, 'strftime'):
                    data_fmt = data_match.strftime('%d/%m/%Y')
                else:
                    data_fmt = str(data_match)
                transacoes_encontradas.append({
                    'data': data_fmt,
                    'descricao': match['descricao'],
                    'valor': match['valor_abs']
                })

            resultados.append({
                'conta': conta,
                'nome_conta': dados['nome_conta'],
                'competencia': competencia,
                'valor_provisao': valor_provisao,
                'encontrado': True,
                'transacoes': transacoes_encontradas
            })
        else:
            resultados.append({
                'conta': conta,
                'nome_conta': dados['nome_conta'],
                'competencia': competencia,
                'valor_provisao': valor_provisao,
                'encontrado': False,
                'transacoes': []
            })

    return resultados

# ======================================================
# INTERFACE PRINCIPAL
# ======================================================
from pathlib import Path

logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
st.markdown(
    f"""
    <div style="text-align:center; margin-top:10px;">
        <img src="data:image/png;base64,{logo_b64}" style="width:480px; height:auto;" />
        <div style="color:#cbd5e1; font-size:0.98rem; margin-top:0px; line-height:1.2;">Sistema de concilia&ccedil;&atilde;o cont&aacute;bil - Provis&otilde;es x Pagamentos</div>
    </div>
    """,
    unsafe_allow_html=True
)
st.divider()

# ======================================================
# ETAPA 1: UPLOAD DO RAZÃO
# ======================================================
if st.session_state.etapa == 1:
    st.markdown("### 📤 1. Upload do Razão Contábil")

    arquivo = st.file_uploader(
        "Selecione o arquivo Excel do razão",
        type=['xlsx', 'xls']
    )

    if arquivo:
        try:
            df_razao = pd.read_excel(arquivo)
            st.success(f"✅ Arquivo carregado: {len(df_razao)} linhas")

            if st.button("🔍 Analisar Provisões", type="primary", use_container_width=True):
                with st.spinner("Processando..."):
                    competencia_inicial = extrair_competencia_inicial(df_razao)
                    provisoes = processar_razao_passivo(df_razao, competencia_inicial)
                    st.session_state.provisoes = provisoes

                if provisoes:
                    st.session_state.etapa = 2
                    st.rerun()
                else:
                    st.error("Nenhuma provisão encontrada.")

        except Exception as e:
            st.error(f"Erro: {str(e)}")

# ======================================================
# ETAPA 2: VISUALIZAR PROVISÕES (MELHOR VERSÃO)
# ======================================================
elif st.session_state.etapa == 2 and tem_provisoes():
    st.markdown("### 📊 2. Provisões Identificadas")

    provisoes = st.session_state.provisoes

    # Resumo
    total_creditos = sum(d['creditos'] for d in provisoes.values())
    total_ajustes = sum(d['ajustes'] for d in provisoes.values())
    saldo_total = total_creditos - total_ajustes

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Contas", len(provisoes))
    with col2:
        st.metric("Total Provisões", f"R$ {total_creditos:,.2f}")
    with col3:
        st.metric("Saldo a Pagar", f"R$ {saldo_total:,.2f}")

    st.divider()

    # Cada conta em um card BONITO e FUNCIONAL
    for (conta, competencia), dados in sorted(provisoes.items()):
        saldo = dados['creditos'] - dados['ajustes']

        # Container principal
        with st.container():
            # Cabeçalho do card
            col_titulo, col_valor = st.columns([3, 1])
            with col_titulo:
                st.markdown(f"**📌 Conta {conta}** – {dados['nome_conta']} ({competencia})")
                st.caption(f"Competência: {competencia} • Lançamentos: {len(dados['lancamentos'])}")
            with col_valor:
                st.markdown(f"**R$ {saldo:,.2f}**")

            # Grid de créditos/ajustes usando HTML SIMPLES mas FUNCIONAL
            html_grid = f"""
            <div style="display: flex; gap: 1rem; margin: 1rem 0;">
                <div style="flex: 1; background: #0f1622; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
                    <div style="color: #93c5fd; font-size: 0.9rem;">Créditos</div>
                    <div style="font-size: 1.2rem; font-weight: bold; color: #f8fafc;">R$ {dados['creditos']:,.2f}</div>
                </div>
                <div style="flex: 1; background: #0f1622; padding: 1rem; border-radius: 8px; border: 1px solid #334155;">
                    <div style="color: #fbbf24; font-size: 0.9rem;">Ajustes</div>
                    <div style="font-size: 1.2rem; font-weight: bold; color: #f8fafc;">R$ {dados['ajustes']:,.2f}</div>
                </div>
            </div>
            """
            st.markdown(html_grid, unsafe_allow_html=True)

            with st.expander("Ver lancamentos considerados"):
                lancamentos = dados.get('lancamentos', [])
                if lancamentos:
                    df_lanc = pd.DataFrame(lancamentos)
                    for col in ['data', 'historico', 'chave', 'contra', 'tipo', 'valor']:
                        if col not in df_lanc.columns:
                            df_lanc[col] = ''
                    df_lanc = df_lanc[['data', 'historico', 'chave', 'contra', 'tipo', 'valor']]
                    st.dataframe(
                        df_lanc.rename(columns={
                            'data': 'Data',
                            'historico': 'Historico',
                            'chave': 'Chave',
                            'contra': 'Contra',
                            'tipo': 'Tipo',
                            'valor': 'Valor'
                        }).style.format({'Valor': 'R$ {:.2f}'}),
                        use_container_width=True
                    )
                    total_considerado = df_lanc['valor'].sum()
                    st.caption(f"Qtde de lancamentos: {len(df_lanc)} | Total considerado: R$ {total_considerado:,.2f}")
                else:
                    st.caption("Qtde de lancamentos: 0 | Total considerado: R$ 0,00")

            st.divider()

    # Botões
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    with col_btn1:
        if st.button("Voltar", use_container_width=True):
            st.session_state.etapa = 1
            st.rerun()

    with col_btn2:
        # Exportar
        dados_export = []
        for (conta, competencia), dados in provisoes.items():
            dados_export.append({
                'Conta': conta,
                'Nome': dados['nome_conta'],
                'Competência': competencia,
                'Créditos': dados['creditos'],
                'Ajustes': dados['ajustes'],
                'Saldo': dados['creditos'] - dados['ajustes']
            })

        df_export = pd.DataFrame(dados_export)
        csv = df_export.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')

        st.download_button(
            label="💾 Exportar",
            data=csv,
            file_name="provisoes.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_btn3:
        if st.button("💰 Importar OFX →", type="primary", use_container_width=True):
            st.session_state.etapa = 3
            st.rerun()

# ======================================================
# ETAPA 3: IMPORTAR EXTRATO
# ======================================================
elif st.session_state.etapa == 3:
    st.markdown("### 💰 3. Importar Extrato Bancário")

    arquivo_ofx = st.file_uploader("Arquivo OFX/QFX", type=['ofx', 'qfx'])

    if arquivo_ofx:
        nome = arquivo_ofx.name.lower()
        raw = arquivo_ofx.getvalue()
        texto_ofx = raw.decode(errors='ignore').lower()
        if 'sicredi' in texto_ofx:
            banco_detectado = "sicredi"
        elif 'sicoob' in texto_ofx:
            banco_detectado = "sicoob"
        else:
            banco_detectado = ""

        st.session_state.ofx_banco_detectado = banco_detectado
        st.session_state.conta_banco_credito_detectada = MAPA_CONTAS_BANCO.get(banco_detectado, "")

        if banco_detectado:
            st.info(f"Banco detectado: {banco_detectado} | Conta credito: {st.session_state.conta_banco_credito_detectada}")
        else:
            st.warning("Banco nÃ£o detectado. Conta crédito não preenchida automaticamente.")

        if nome.endswith(('.ofx', '.qfx')):
            transacoes = ler_ofx(io.BytesIO(raw))
        else:
            st.error("Envie um arquivo .ofx ou .qfx")
            transacoes = pd.DataFrame(columns=['data', 'descricao', 'valor'])

        transacoes = transacoes[transacoes['valor'] < 0].copy()
        st.session_state.transacoes_ofx = transacoes

        st.success(f"✅ {len(transacoes)} transações carregadas")

        # Mostrar transações
        st.markdown("#### 📄 Transações do Extrato")

        transacoes_display = transacoes.copy()
        transacoes_display['tipo'] = 'Pagamento'
        transacoes_display['valor_exibicao'] = transacoes_display['valor'].abs()

        st.dataframe(
            transacoes_display[['data', 'descricao', 'valor_exibicao', 'tipo']]
            .rename(columns={'valor_exibicao': 'valor'})
            .style.format({'valor': 'R$ {:.2f}'}),
            use_container_width=True
        )

        # Botões
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Voltar", use_container_width=True):
                st.session_state.etapa = 2
                st.rerun()

        with col_btn2:
            if st.button("🔍 Conciliação →", type="primary", use_container_width=True):
                st.session_state.etapa = 4
                st.rerun()

# ======================================================
# ETAPA 4: CONCILIAÇÃO
# ======================================================
elif st.session_state.etapa == 4 and tem_provisoes() and tem_ofx():
    st.markdown("### 🔄 4. Resultado da Conciliação")

    provisoes = st.session_state.provisoes
    transacoes_ofx = st.session_state.transacoes_ofx

    with st.spinner("Buscando correspondências..."):
        resultados = buscar_correspondencias(provisoes, transacoes_ofx)

    dados_conciliados = []
    for resultado in resultados:
        if resultado['encontrado']:
            for trans in resultado['transacoes']:
                dados_conciliados.append({
                    'data_pagto': trans.get('data', ''),
                    'valor_pago': trans.get('valor', 0),
                    'valor_provisao': resultado.get('valor_provisao', 0),
                    'conta_provisao': resultado.get('conta', ''),
                    'competencia': resultado.get('competencia', ''),
                    'descricao': trans.get('descricao', ''),
                    'descricao_ofx': trans.get('descricao', ''),
                    'descricao_func': trans.get('nome_func', ''),
                    'nome_conta': resultado.get('nome_conta', ''),
                    'chave': trans.get('chave', ''),
                    'participante_debito': trans.get('participante_debito', '')
                })
    st.session_state.df_conciliados = pd.DataFrame(dados_conciliados)

    encontrados = sum(1 for r in resultados if r['encontrado'])
    total = len(resultados)

    st.success(f"✅ {encontrados} de {total} provisões encontradas")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Provisões", total)
    with col2:
        st.metric("Encontradas", encontrados)

    st.divider()

    # Resultados
    filtro = st.selectbox(
        "Filtro de resultados",
        ["Todos", "Encontrados", "Nao encontrados"],
        index=0
    )

    for resultado in resultados:
        if filtro == "Encontrados" and not resultado['encontrado']:
            continue
        if filtro == "Nao encontrados" and resultado['encontrado']:
            continue
        if resultado.get('folha'):
            total_pago = resultado.get('total_pago', 0.0)
            total_pendente = resultado.get('total_pendente', 0.0)
            status_total = resultado.get('status_total', 'PENDENTE')
            if status_total in ['PARCIAL', 'QUITADO']:
                status_label = status_total
            else:
                status_label = "PENDENTE"
            cor = "#10b981" if status_label in ["ENCONTRADO", "QUITADO"] else ("#f59e0b" if status_label == "PARCIAL" else "#ef4444")
            bg = "#f0fdf4" if status_label in ["ENCONTRADO", "QUITADO"] else ("#fffbeb" if status_label == "PARCIAL" else "#fef2f2")
            st.markdown(f"""
            <div style="background: {bg}; color: #0f172a; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid {cor};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>🧾 {resultado['conta']} - {resultado['nome_conta']} ({resultado.get('competencia','')})</strong><br>
                        <small>Provisionado: R$ {resultado['valor_provisao']:,.2f} | Pago no banco: R$ {total_pago:,.2f} | Pendente: R$ {total_pendente:,.2f}</small>
                    </div>
                    <span style="background: {cor}; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem;">
                        {status_label}
                    </span>
                </div>
            """, unsafe_allow_html=True)

            conciliados = resultado.get('conciliados_func', [])
            pendentes = resultado.get('pendentes_func', [])

            if conciliados:
                st.markdown("**Conciliados por funcionario**")
                for item in conciliados:
                    st.markdown(f"- {item['nome_func']} • R$ {item['valor']:,.2f} • {item.get('data','')}")

            if pendentes:
                st.markdown("**Pendentes (provavel caixa)**")
                for item in pendentes:
                    st.markdown(f"- {item['nome_func']} • R$ {item['valor']:,.2f}")

            if resultado['transacoes']:
                st.markdown("**Pagamentos no banco**")
                for trans in resultado['transacoes']:
                    st.markdown(f"- {trans['data']} • {trans['descricao']} • R$ {trans['valor']:,.2f}")

            lancamentos_razao = resultado.get('lancamentos_razao', [])
            qt_lanc = len(lancamentos_razao)
            qt_pag = len(resultado.get('transacoes', []))
            st.caption(f"Qtde lancamentos: {qt_lanc} | Total considerado: R$ {resultado.get('total_provisao', 0):,.2f}")
            st.caption(f"Qtde pagamentos: {qt_pag} | Total pago (banco): R$ {total_pago:,.2f} | Pendente: R$ {total_pendente:,.2f}")

            with st.expander("Ver lancamentos considerados"):
                if lancamentos_razao:
                    df_lanc = pd.DataFrame(lancamentos_razao)
                    for col in ['data', 'historico', 'chave', 'contra', 'tipo', 'valor']:
                        if col not in df_lanc.columns:
                            df_lanc[col] = ''
                    df_lanc = df_lanc[['data', 'historico', 'chave', 'contra', 'tipo', 'valor']]
                    st.dataframe(
                        df_lanc.rename(columns={
                            'data': 'Data',
                            'historico': 'Historico',
                            'chave': 'Chave',
                            'contra': 'Contra',
                            'tipo': 'Tipo',
                            'valor': 'Valor'
                        }).style.format({'Valor': 'R$ {:.2f}'}),
                        use_container_width=True
                    )
                else:
                    st.caption("Qtde de lancamentos: 0 | Total considerado: R$ 0,00")

            with st.expander("Pagamentos do banco usados"):
                transacoes = resultado.get('transacoes', [])
                if transacoes:
                    df_pag = pd.DataFrame(transacoes)
                    st.dataframe(
                        df_pag.rename(columns={
                            'data': 'Data',
                            'descricao': 'Descricao',
                            'valor': 'Valor'
                        }).style.format({'Valor': 'R$ {:.2f}'}),
                        use_container_width=True
                    )
                else:
                    st.caption("Qtde de pagamentos: 0 | Total pago: R$ 0,00")

            st.markdown("</div>", unsafe_allow_html=True)
        elif resultado['encontrado']:
            # ENCONTRADO - Verde
            st.markdown(f"""
            <div style="background: #f0fdf4; color: #0f172a; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #10b981;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>✅ {resultado['conta']} - {resultado['nome_conta']} ({resultado.get('competencia','')})</strong><br>
                        <small>Provisionado: R$ {resultado['valor_provisao']:,.2f}</small>
                    </div>
                    <span style="background: #10b981; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem;">
                        ENCONTRADO
                    </span>
                </div>
            """, unsafe_allow_html=True)

            # Mostrar pagamentos encontrados
            for trans in resultado['transacoes']:
                st.markdown(f"""
                <div style="margin-left: 1rem; margin-top: 0.5rem;">
                    • <strong>{trans['data']}</strong> - {trans['descricao']}<br>
                    &nbsp;&nbsp;Valor: R$ {trans['valor']:,.2f}
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            # NÃO ENCONTRADO - Vermelho
            st.markdown(f"""
            <div style="background: #fef2f2; color: #0f172a; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #ef4444;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>❌ {resultado['conta']} - {resultado['nome_conta']} ({resultado.get('competencia','')})</strong><br>
                        <small>Provisionado: R$ {resultado['valor_provisao']:,.2f}</small>
                    </div>
                    <span style="background: #ef4444; color: white; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem;">
                        NÃO ENCONTRADO
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Botões finais
    st.divider()
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    with col_btn1:
        if st.button("Voltar", use_container_width=True):
            st.session_state.etapa = 3
            st.rerun()

    with col_btn2:
        # Exportar resultados
        dados_export = []
        for resultado in resultados:
            if resultado['encontrado']:
                for trans in resultado['transacoes']:
                    dados_export.append({
                        'Conta': resultado['conta'],
                        'Nome': resultado['nome_conta'],
                        'Valor_Provisionado': resultado['valor_provisao'],
                        'Data_Pagamento': trans['data'],
                        'Descricao': trans['descricao'],
                        'Valor_Pago': trans['valor'],
                        'Status': 'CONCILIADO'
                    })
            else:
                dados_export.append({
                    'Conta': resultado['conta'],
                    'Nome': resultado['nome_conta'],
                    'Valor_Provisionado': resultado['valor_provisao'],
                    'Data_Pagamento': '',
                    'Descricao': 'NÃO ENCONTRADO',
                    'Valor_Pago': 0,
                    'Status': 'PENDENTE'
                })

        df_export = pd.DataFrame(dados_export)
        csv = df_export.to_csv(index=False, sep=';', decimal=',', encoding='utf-8-sig')

        st.download_button(
            label="📄 Exportar Resultado",
            data=csv,
            file_name="conciliacao.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_btn4:
        if st.button("Exportar TXT SCI", use_container_width=True):
            st.session_state.etapa = 5
            st.rerun()

    with col_btn3:
        if st.button("🔄 Nova Análise", type="primary", use_container_width=True):
            # Limpar tudo
            for key in ['etapa', 'provisoes', 'transacoes_ofx']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# ======================================================
# ETAPA 5: EXPORTAR TXT SCI
# ======================================================
elif st.session_state.etapa == 5:
    st.markdown("### 5. Exportar TXT SCI")

    df_conciliados = st.session_state.get('df_conciliados')
    if df_conciliados is None or df_conciliados.empty:
        st.warning("NÃ£o hÃ¡ pagamentos conciliados para exportar.")
    else:
        conta_detectada = st.session_state.get('conta_banco_credito_detectada', "")
        conta_banco = ""
        if conta_detectada:
            conta_banco = st.text_input("Conta Crédito (Banco)", value=conta_detectada)
        else:
            opcoes = [f"{k} ({v})" for k, v in MAPA_CONTAS_BANCO.items()]
            escolha = st.selectbox("Conta Crédito (Banco)", opcoes)
            conta_banco = MAPA_CONTAS_BANCO[escolha.split()[0]]
        cod_hist = st.text_input("Código de Histórico", value="1001")
        txt = exportar_txt_sci_pagamentos(
            df_conciliados,
            conta_banco=conta_banco,
            cod_hist=cod_hist
        )

        st.download_button(
            label="Baixar TXT SCI",
            data=txt,
            file_name="exportacao_sci.txt",
            mime="text/plain",
            use_container_width=True
        )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Voltar", use_container_width=True):
            st.session_state.etapa = 4
            st.rerun()

# ======================================================
# RODAPÉ
# ======================================================
st.divider()
st.caption("Conciliador PRO • Sistema de conciliação contábil")



