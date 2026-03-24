import streamlit as st
import unicodedata
import pandas as pd
import io
import re
from pypdf import PdfWriter, PdfReader

# 1. CONFIGURAÇÃO DA PÁGINA (Deve ser o primeiro comando)
st.set_page_config(page_title="NandoTools - Multi-Ferramentas", layout="wide", page_icon="🛠️")

# --- 2. FUNÇÕES DE SUPORTE (Lógica isolada para evitar erros de indentação) ---
def limpar_caracteres_ilegais(df):
    return df.applymap(
        lambda x: re.sub(r'[\x00-\x1F\x7F]', '', x) if isinstance(x, str) else x
    )
    
    # Aplicamos a remoção em todas as colunas de texto (object)
    return df.applymap(lambda x: illegal_char_re.sub("", x) if isinstance(x, str) else x)
def corrigir_estrutura_csv(file_buffer, separador, total_colunas_esperado):
    output = []
    file_buffer.seek(0)
    for linha_binaria in file_buffer:
        # Tenta decodificar de forma segura
        try:
            linha_texto = linha_binaria.decode("utf-8").strip()
        except UnicodeDecodeError:
            linha_texto = linha_binaria.decode("iso-8859-1").strip()
            
        if not linha_texto:
            continue
        
        contagem_atual = linha_texto.count(separador)
        objetivo = total_colunas_esperado - 1
        
        if contagem_atual < objetivo:
            linha_texto += (separador * (objetivo - contagem_atual))
        
        output.append(linha_texto)
    return "\n".join(output)


# --- 3. INTERFACE PRINCIPAL ---

st.sidebar.title("NandoTools 🛠️")
st.sidebar.markdown("---")
opcao = st.sidebar.radio(
    "Selecione a Ferramenta:",
    ["Home", "Validar/Corrigir CSV", "Mesclar PDF", "Manipulador de Texto", "PROCV Dinâmico"]
)

if opcao == "Home":
    st.title("Bem-vindo ao NandoTools")
    st.info("Utilize o menu lateral para navegar entre as ferramentas disponíveis.")
    st.markdown("""
    ### Ferramentas disponíveis:
    * **CSV Validator:** Valida e corrige a estrutura de arquivos CSV gigantes.
    * **PDF Merger:** Une vários arquivos PDF em um único documento.
    * **Text Tools:** Manipulação rápida de cases (Maiúsculas/Minúsculas).
    * **PROCV Dinâmico:** Compara e une dados de dois arquivos Excel/CSV.
    """)

elif opcao == "Validar/Corrigir CSV":
    st.title("🧐 Validador e Corretor de CSV")

# --- INTERFACE ---
    st.title("🛠️ Nando CSV Tool")

    # Criando abas para organizar o serviço
    tab_validador, tab_corretor = st.tabs(["🧐 Validador de Estrutura", "🔧 Corretor de Colunas"])

    with tab_validador:
        uploaded_file = st.file_uploader("Suba seu arquivo CSV para análise", type="csv", key="validador")

        if uploaded_file:
            # --- LEITURA RESILIENTE DA PRIMEIRA LINHA ---
            conteudo_bruto = uploaded_file.readline()
            try:
                # Tenta UTF-8 (Padrão moderno)
                primeira_linha = conteudo_bruto.decode("utf-8").strip()
            except UnicodeDecodeError:
                # Se falhar, usa ISO-8859-1 (Padrão Excel/Windows Brasil)
                primeira_linha = conteudo_bruto.decode("iso-8859-1").strip()
            
            # Identificação do separador e colunas
            sep = ";" if primeira_linha.count(";") > primeira_linha.count(",") else ","
            qtd_esperada = len(primeira_linha.split(sep))
            uploaded_file.seek(0) # Volta para o início para o validador/corretor poder ler tudo

            st.info(f"Separador: `{sep}` | Colunas esperadas: **{qtd_esperada}**")

            if st.button("Iniciar Validação"):
                erros = []
                total = 0
                for idx, linha in enumerate(uploaded_file):
                    total += 1
                    # --- DECODIFICAÇÃO SEGURA POR LINHA ---
                    try:
                        txt = linha.decode("utf-8").strip()
                    except UnicodeDecodeError:
                        try:
                            # Tenta o padrão Windows/Brasil
                            txt = linha.decode("iso-8859-1").strip()
                        except UnicodeDecodeError:
                            # Tenta UTF-16 (comum para o erro 0xff)
                            txt = linha.decode("utf-16").strip()
                    
                    if not txt: continue
                    
                    # Validação da quantidade de colunas
                    if len(txt.split(sep)) != qtd_esperada:
                        erros.append(f"Linha {idx+1}: {txt[:50]}...")
                
                # Guardando no session_state para não perder ao clicar em botões
                st.session_state['erros'] = erros
                st.session_state['total'] = total
                st.session_state['sep'] = sep
                st.session_state['qtd'] = qtd_esperada

            # Exibição de Resultados (se existirem no estado)
            if 'erros' in st.session_state:
                st.divider()
                c1, c2 = st.columns(2)
                c1.metric("Linhas Processadas", st.session_state['total'])
                c2.metric("Inconsistências", len(st.session_state['erros']), delta=len(st.session_state['erros']), delta_color="inverse")

                if st.session_state['erros']:
                    st.error("Clique na aba **Corretor de Colunas** para baixar uma versão corrigida.")
                    with st.expander("Ver logs de erro"):
                        st.write(st.session_state['erros'][:100])

    with tab_corretor:
        st.subheader("Ajuste automático de linhas")
        if 'erros' in st.session_state and len(st.session_state['erros']) > 0:
            st.write(f"Detectamos {len(st.session_state['erros'])} linhas curtas. Deseja completar com `{st.session_state['sep']}`?")
            
            if st.button("Gerar Arquivo Corrigido"):
                with st.spinner("Reestruturando linhas..."):
                    # Usamos o arquivo que ainda está no buffer do uploader
                    csv_fix = corrigir_estrutura_csv(uploaded_file, st.session_state['sep'], st.session_state['qtd'])
                    st.success("Arquivo pronto!")
                    st.download_button(
                        label="⬇️ Baixar CSV Corrigido",
                        data=csv_fix,
                        file_name="corrigido_nandotools.csv",
                        mime="text/csv"
                    )
        else:
            st.info("Nenhum erro de coluna curta detectado ou arquivo ainda não validado.")

elif opcao == "Mesclar PDF":
    st.title("📄 Mesclador de PDF")
    
    arquivos_pdf = st.file_uploader(
    "Escolha os arquivos PDF (múltipla seleção permitida). Máximo de 1 GB por arquivo", 
    type="pdf", 
    accept_multiple_files=True
)

    if arquivos_pdf:
        # Criamos um dicionário para mapear o nome do arquivo ao objeto do arquivo
        mapa_arquivos = {pdf.name: pdf for pdf in arquivos_pdf}
        nomes_arquivos = list(mapa_arquivos.keys())

        st.subheader("Configuração da Ordem")
        
        # 2. Interface de Reordenação
        # O multiselect virá pré-preenchido com todos os arquivos
        ordem_final = st.multiselect(
            "Verifique ou altere a ordem de junção:",
            options=nomes_arquivos,
            default=nomes_arquivos
        )

        st.info("💡 O primeiro da lista será o topo do documento final.")

        # 3. Processamento
        if st.button("Unir e Gerar PDF"):
            if not ordem_final:
                st.warning("Por favor, selecione pelo menos um arquivo na lista de ordem.")
            else:
                merger = PdfWriter()
                
                with st.spinner('Processando PDFs...'):
                    for nome in ordem_final:
                        arquivo_obj = mapa_arquivos[nome]
                        merger.append(arquivo_obj)
                    
                    output = io.BytesIO()
                    merger.write(output)
                    merger.close()
                
                st.success("✨ Tudo pronto!")
                
                # 4. Download
                st.download_button(
                    label="📥 Baixar PDF Mesclado",
                    data=output.getvalue(),
                    file_name="pdf_final_combinado.pdf",
                    mime="application/pdf"
                )

elif opcao == "Manipulador de Texto":
    # --- 1. FUNÇÕES DE LIMPEZA (Coloque dentro do elif ou no topo do arquivo) ---
    def remover_acentos(texto):
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

    def formato_frase(texto):
        # Converte para minúscula e capitaliza apenas a primeira letra da string
        return texto.lower().capitalize()

    def limpar_espacos(texto):
    # Remove espaços duplicados, espaços no início e no fim
        return " ".join(texto.split())

    st.title("🔤 Manipulador de Texto")

    # --- 2. CSS PARA BOTÕES EM LINHA ÚNICA (Igual ao original) ---
    st.markdown("""
    <style>
        [data-testid="column"] {
            flex: 1 1 0% !important;
            min-width: 0 !important;
            padding: 0px 2px !important;
        }
        .stButton > button {
            width: 100% !important;
            white-space: nowrap !important;
            font-size: 12px !important;
            padding: 0.25rem 0.5rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- 3. ÁREA DE TEXTO ---
    # Inicializa o estado se não existir
    if 'texto_input' not in st.session_state:
        st.session_state.texto_input = ""

    st.session_state.texto_input = st.text_area(
        "Escreva ou cole o seu texto aqui:", 
        value=st.session_state.texto_input, 
        height=250
    )

    # Métricas
    st.caption(f"Letras: {len(st.session_state.texto_input)} | Palavras: {len(st.session_state.texto_input.split())}")
    st.markdown("---")

    # --- 4. BOTÕES EM COLUNAS ---
    cols = st.columns(7)

    with cols[0]:
        if st.button("Formato Frase"):
            st.session_state.texto_input = formato_frase(st.session_state.texto_input)
            st.rerun()
    with cols[1]:
        if st.button("minúscula"):
            st.session_state.texto_input = st.session_state.texto_input.lower()
            st.rerun()
    with cols[2]:
        if st.button("MAIÚSCULA"):
            st.session_state.texto_input = st.session_state.texto_input.upper()
            st.rerun()
    with cols[3]:
        if st.button("Formato Título"):
            st.session_state.texto_input = st.session_state.texto_input.title()
            st.rerun()
    with cols[4]:
        if st.button("Limpar Espaços Extras"):
            st.session_state.texto_input = limpar_espacos(st.session_state.texto_input)
            st.rerun()
    with cols[5]:
        if st.button("Sem Acento"):
            st.session_state.texto_input = remover_acentos(st.session_state.texto_input)
            st.rerun()
    with cols[6]:
        if st.button("Limpar"):
            st.session_state.texto_input = ""
            st.rerun()

elif opcao == "PROCV Dinâmico":
    st.title("📊 PROCV Dinâmico")
    
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("1. Tabela Principal")
        file1 = st.file_uploader("Arquivo base (onde os dados entrarão)", type=['csv', 'xlsx', 'xls'], key="file1")

    with col_b:
        st.subheader("2. Tabela de Referência")
        file2 = st.file_uploader("Arquivo de busca (onde os dados estão)", type=['csv', 'xlsx', 'xls'], key="file2")

    def load_data(file):
        if file.name.endswith('.csv'):
            encodings = ['utf-8', 'utf-16', 'iso-8859-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    file.seek(0)
                    df = pd.read_csv(file, sep=None, encoding=encoding, engine='python')
                    
                    # 🔥 valida se veio "quebrado" (com muitos \x00)
                    if df.astype(str).apply(lambda col: col.str.contains('\x00')).any().any():
                        continue
                    
                    return df
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue

            st.error(f"Não foi possível ler o arquivo {file.name}. Verifique a codificação.")
            return None
        else:
            return pd.read_excel(file)

    if file1 and file2:
        # Carregamento dos dados
        df_main = load_data(file1)
        df_ref = load_data(file2)

        st.divider()
    
    # Interface para escolha das chaves
        st.subheader("🔗 Mapeamento de Colunas")
        c1, c2 = st.columns(2)
    
        with c1:
            key_main = st.selectbox("Identificador na Tabela Principal:", df_main.columns)
        with c2:
            key_ref = st.selectbox("Identificador na Tabela de Referência:", df_ref.columns)

    # Escolha de quais colunas da tabela de referência o usuário quer trazer
        cols_to_bring = st.multiselect(
            "Selecione as colunas da Referência que deseja adicionar à Principal:",
            [c for c in df_ref.columns if c != key_ref]
    )

        if st.button("Executar Cruzamento de dados"):
            if not cols_to_bring:
                st.warning("Selecione as colunas para trazer.")
            else:
                def normalizar_chave(col):
                    return (
                        col.fillna('')  # 🔥 remove NaN
                        .astype(str)
                        .str.replace(r'\.0$', '', regex=True)
                        .str.replace(r'[\x00-\x1F\x7F]', '', regex=True)
                        .str.strip()
                        .str.lower()
                    )

                # 🔥 APLICAÇÃO NAS CHAVES
                df_main[key_main] = normalizar_chave(df_main[key_main])
                df_ref[key_ref] = normalizar_chave(df_ref[key_ref])
                
                st.write("Preview chave main:", df_main[key_main].head())
                st.write("Preview chave ref:", df_ref[key_ref].head())
                
                # 2. Cruzamento
                df_ref_filtered = df_ref[[key_ref] + cols_to_bring]
                resultado = pd.merge(df_main, df_ref_filtered, left_on=key_main, right_on=key_ref, how='left')
                resultado = resultado.drop(columns=[key_ref])
                resultado = limpar_caracteres_ilegais(resultado)
                st.success("Cruzamento concluído!")
                st.dataframe(resultado.head(10))

                # --- TUDO ABAIXO DEVE ESTAR IDENTADO DENTRO DO IF ---
                st.divider()
                st.subheader("📥 Baixar Resultado")
                
                btn_col1, btn_col2 = st.columns(2)

                with btn_col1:
                    output_excel = io.BytesIO()
                    # engine='openpyxl' é essencial para .xlsx
                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        resultado.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="Baixar em Excel (.xlsx)",
                        data=output_excel.getvalue(),
                        file_name="resultado_procv.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                with btn_col2:
                    output_csv = resultado.to_csv(index=False).encode('utf-8-sig')
                    
                    st.download_button(
                        label="Baixar em CSV (.csv)",
                        data=output_csv,
                        file_name="resultado_procv.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                    
                