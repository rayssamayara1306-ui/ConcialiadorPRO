# regras.py

# ======================================================
# LISTA TÃ‰CNICA DE CONTAS DE PROVISÃƒO (FORMA 1)
# ======================================================
# ðŸ‘‰ Se a conta estiver aqui, ela Ã‰ provisÃ£o.
# ðŸ‘‰ Para adicionar nova conta de passivo, Ã© SÃ“ incluir aqui.

CONTAS_PROVISAO = {
    '160': 'Salarios a Pagar',
    '163': '13º Salário a Pagar',
    '169': 'Pro-labore a Pagar',
    '161': 'Férias a pagar',
    '162': 'Rescisões a Pagar',
    '172': 'FGTS a Pagar',
    '196': 'COFINS a Pagar',
    '197': 'PIS a Pagar',
    '642': 'Contribuição Assistencial a Pagar',
    '708': 'DARF Previdenciário a Pagar',
    '191': 'CSLL S/ Lucro Real a Pagar',
    '1781': 'IRPJ S/ Lucro Real a Pagar',
}


CONTAS_FOLHA = {
  '160': 'Salarios a Pagar',
  '163': '13o Salario a Pagar',
  '169': 'Pro-labore a Pagar',
  '161': 'Ferias a Pagar',
  '162': 'Rescisoes a Pagar',
}

PALAVRAS_AJUSTE = [
    'ajuste',
    'correção',
    'compensação',
    'reverssão',
    'provisão a menor'
]

MAPA_CONTAS_BANCO = {
    "sicredi": "2404",
    "sicoob": "2376",
}



