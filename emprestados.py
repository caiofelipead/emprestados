import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import io


# --- FUNÇÃO ÚNICA E COMBINADA ---
def extrair_jogos_e_minutos(url: str) -> dict:
    """
    Função final. Em uma única visita à URL, ela:
    1. Conta o número total de jogos (incluindo "suplente não utilizado").
    2. Extrai o valor de minutos totais, procurando em dois lugares diferentes para garantir.
    """
    if not isinstance(url, str) or not url.startswith('http'):
        return {"jogos": "Link inválido", "minutos": "Link inválido"}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"jogos": f"Erro HTTP {response.status_code}", "minutos": f"Erro HTTP {response.status_code}"}

        soup = BeautifulSoup(response.text, 'html.parser')

        resultados = {"jogos": "Não encontrado", "minutos": "Não encontrado"}

        # Seletor para a tabela principal de jogos detalhados
        seletor_css_tabela_jogos = "#tm-main > div.row > div.large-8.columns > div:nth-child(2) > div.responsive-table > table"
        tabela_jogos = soup.select_one(seletor_css_tabela_jogos)

        if tabela_jogos:
            # --- LÓGICA 1: Contar os Jogos (VERSÃO CORRIGIDA E PRECISA) ---
            # Este bloco foi substituído pela nossa lógica mais recente e robusta.
            tbodys = tabela_jogos.find_all('tbody')
            if tbodys:
                contador_de_jogos = 0
                for tbody in tbodys:
                    for linha in tbody.find_all('tr'):
                        # Critério robusto: a linha não é um sub-cabeçalho e tem células.
                        # Isso garante a contagem dos jogos em que foi "suplente não utilizado".
                        classes_da_linha = linha.get('class', [])
                        celulas = linha.find_all('td')
                        if 'tm-subheader' not in classes_da_linha and len(celulas) > 5:
                            contador_de_jogos += 1
                resultados["jogos"] = str(contador_de_jogos)

            # --- LÓGICA 2: Extrair o Total de Minutos (A QUE VOCÊ GOSTOU, COM PLANO A/B) ---
            # Esta parte foi mantida exatamente como no código que você enviou.
            # PLANO A: Procurar no rodapé (tfoot) da tabela principal
            tfoot = tabela_jogos.find('tfoot')
            if tfoot:
                celulas_total = tfoot.find_all('td')
                if celulas_total and len(celulas_total) > 2:
                    total_minutos = celulas_total[-1].get_text(strip=True)
                    resultados["minutos"] = total_minutos

            # PLANO B: Se o Plano A falhou (minutos ainda "Não encontrado"), procurar na tabela de resumo superior
            if resultados["minutos"] == "Não encontrado":
                tabela_resumo = soup.find('table', class_='items')
                if tabela_resumo:
                    primeira_linha_dados = tabela_resumo.find('tbody').find('tr')
                    if primeira_linha_dados:
                        celulas_resumo = primeira_linha_dados.find_all('td')
                        if celulas_resumo:
                            total_minutos_resumo = celulas_resumo[-1].get_text(strip=True)
                            resultados["minutos"] = total_minutos_resumo

        return resultados

    except Exception as e:
        return {"jogos": f"Erro: {e}", "minutos": f"Erro: {e}"}


# --- INTERFACE GRÁFICA COM STREAMLIT ---
# (Nenhuma mudança na interface, ela continua a mesma)

st.set_page_config(page_title="Scraper de Jogos e Minutos", layout="wide")
st.title("⚽ Scraper Final - Jogos e Minutos (Transfermarkt)")
st.markdown("Esta versão extrai a **Contagem de Jogos** (incluindo banco) e o **Total de Minutos**.")

uploaded_file = st.file_uploader("1. Selecione a sua planilha Excel", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.dataframe(df.head())

    st.header("Configurações")
    link_column = st.selectbox(
        "2. Selecione a coluna que contém os links:",
        df.columns
    )

    if st.button("🚀 Iniciar Extração (Jogos e Minutos)", type="primary"):
        total_rows = len(df)
        st.info(f"Iniciando extração para {total_rows} linhas...")
        progress_bar = st.progress(0)
        status_text = st.empty()

        lista_jogos = []
        lista_minutos = []

        for index, row in df.iterrows():
            url = row[link_column]
            status_text.text(f"Processando {index + 1}/{total_rows}...")

            dados = extrair_jogos_e_minutos(url)

            lista_jogos.append(dados.get("jogos", "Erro"))
            lista_minutos.append(dados.get("minutos", "Erro"))

            progress_bar.progress((index + 1) / total_rows)
            time.sleep(0.5)

        status_text.success("Extração concluída!")

        df["Jogos_Relacionados"] = lista_jogos # Renomeei para maior clareza
        df["Minutos_Totais"] = lista_minutos

        st.session_state['df_processed'] = df.copy()
        st.header("Resultados Finais")
        st.dataframe(df)

if 'df_processed' in st.session_state:
    st.header("Download")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openxl') as writer:
        st.session_state['df_processed'].to_excel(writer, index=False, sheet_name='Jogos_e_Minutos')

    st.download_button(
        label="📥 Baixar Planilha Atualizada",
        data=output.getvalue(),
        file_name="planilha_jogos_e_minutos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )