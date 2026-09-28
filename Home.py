import pandas as pd
import streamlit as st
import altair as alt
import urllib.parse # Keep for sharing links

# -------------------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------------------
st.set_page_config(
    page_title="Paradigma Politico",
    page_icon="⚛️",
    layout="wide",
)

# -------------------------------------------------------------------------
# App URL Placeholder (REPLACE THIS WHEN DEPLOYED)
# -------------------------------------------------------------------------
APP_URL = "https://YOUR_APP_DEPLOYED_URL_HERE" # IMPORTANT: Replace this!

# -------------------------------------------------------------------------
# Custom Color Map for Affinity Chart
# -------------------------------------------------------------------------
party_color_map = {
    "PS": "#FF1493", "AD": "orange", "Livre": "#7FFF00", "PAN": "forestgreen",
    "IL": "cyan", "BE": "#FFC0CB", "CDU": "#EE0000", "Chega": "blue",
    "RIR": "yellow", "JPP": "#7FFFD4", "ADN": "darkgrey", "PCTP/MRPP": "#8B2323",
    "Nova Direita": "lightskyblue", "Volt": "purple",
}
# -------------------------------------------------------------------------
# CSS Styling (Final Attempt: Type Primary + Specific Selector + Target Colors)
# -------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* --- General Text & Background --- */
    body { background-color: #0E1117 !important; }
    .stApp { background-color: #0E1117 !important; }
    h1, h2, h3, h4, h5, h6, p, div, span, label, input, textarea, li { color: #FFFFFF !important; }
    a { color: #1E90FF !important; }

    /* --- Altair Chart Visibility --- */
    .vega-visualization { background-color: transparent !important; }
    .vega-visualization svg text { fill: #FFFFFF !important; font-size: 11px; }
    .vega-visualization svg .axis-title { font-size: 13px !important; fill: #E0E0E0 !important; }
    .vega-visualization svg .legend-title { font-size: 13px !important; fill: #E0E0E0 !important; }
    .vega-visualization svg .legend-label { fill: #CCCCCC !important; font-size: 11px !important; }
    .vega-visualization svg .axis path, .vega-visualization svg .axis line, .vega-visualization svg .axis .tick { stroke: #CCCCCC !important; }
    .vega-visualization svg .axis .domain { stroke-width: 1px; }
    .compass-text-label { fill: #FFFFFF !important; }

    /* --- Button Styling --- */
    /* Answer Buttons (Horizontal) */
    div[data-testid="stHorizontalBlock"] button { width: 100%; color: #ffffff !important; border-radius: 4px; border: none;}
    div[data-testid="stHorizontalBlock"] > div:nth-of-type(1) button { background-color: #8B0000 !important; }
    div[data-testid="stHorizontalBlock"] > div:nth-of-type(2) button { background-color: #FF6347 !important; }
    div[data-testid="stHorizontalBlock"] > div:nth-of-type(3) button { background-color: #FFD700 !important; color: #000000 !important;}
    div[data-testid="stHorizontalBlock"] > div:nth-of-type(4) button { background-color: #556B2F !important; }
    div[data-testid="stHorizontalBlock"] > div:nth-of-type(5) button { background-color: #006400 !important; }

    /* **MODIFIED**: Skip Button Styling (Specific Selector + Target Colors) */
    .skip-btn-wrapper { margin-top: 15px !important; margin-bottom: 5px !important; }
    .skip-btn-wrapper div[data-testid="stButton"] button {
        background-color: #D3D3D3 !important; /* Light Gray */
        color: #000000 !important; /* Black Text */
        width: 100% !important;
        padding: 0.5em 1em !important;
        font-weight: bold;
        border: none !important;
        border-radius: 4px;
    }
    /* Force color on potential inner elements too */
    .skip-btn-wrapper button * {
         color: #000000 !important;
    }


    /* **MODIFIED**: Back Button Styling (Specific Selector + Target Colors) */
    .recuar-btn-wrapper { margin-top: 10px !important; margin-bottom: 10px !important; }
    .recuar-btn-wrapper div[data-testid="stButton"] button {
        background-color: #D3D3D3 !important; /* Light Gray */
        color: #000000 !important; /* Black Text */
        width: 100% !important;
        padding: 0.5em 1em !important;
        font-weight: bold;
        border: none !important;
        border-radius: 4px;
    }
     /* Force color on potential inner elements too */
    .recuar-btn-wrapper button * {
         color: #000000 !important;
    }

    /* **NEW**: Restart Button Wrapper (for spacing) */
    .restart-btn-wrapper {
        margin-top: 20px !important; /* Add space above the restart button */
        margin-bottom: 10px !important; /* Optional: Add space below */
    }
    /* No specific style needed for the button itself - use theme default */


    /* (Rest of CSS: Start/Midpoint/Share/Expander styles remain the same) */
    /* ... */
    .start-btn button, .midpoint-btn button { font-weight: bold !important; padding: 0.6em 1em !important; width: 100%; border-radius: 5px; border: none;}
    .start-btn button { background-color: #003300 !important; color: #ffffff !important; font-size: 1.1rem !important; }
    .midpoint-btn button { background-color: #003366 !important; color: #ffffff !important; font-size: 1.0rem !important; margin-top: 10px;}
    .start-btn-container { display: flex; justify-content: center; margin-top: 20px; gap: 20px;}
    .share-btn { display: inline-block; padding: 8px 15px; margin: 5px 3px; border-radius: 5px; color: white !important; text-decoration: none; font-weight: bold; text-align: center; border: none; cursor: pointer; }
    .share-btn:hover { opacity: 0.9; text-decoration: none; color: white !important; }
    .share-btn-facebook { background-color: #1877F2; } .share-btn-x { background-color: #1DA1F2; }
    .share-btn-whatsapp { background-color: #25D366; } .share-btn-email { background-color: #777777; }
    .share-button-container { text-align: center; margin-top: 20px;}
    .stExpander div[data-testid="stExpanderDetails"] { background-color: #222222; padding: 15px; border-radius: 5px; border: 1px solid #444444; }
    .stExpander div[data-testid="stExpanderDetails"] p, .stExpander div[data-testid="stExpanderDetails"] li, .stExpander div[data-testid="stExpanderDetails"] strong { color: #FFFFFF !important; }
    .stExpander div[data-testid="stExpanderDetails"] a { color: #90CAF9 !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------------------------------
# Constants and Data Loading
# -------------------------------------------------------------------------
# (Code remains the same - assumes CSV loading handles 'Curto' column)
CSV_FILE = "paradigma_politico.csv"
NUM_ECONOMIC_QUESTIONS = 20
NUM_SOCIAL_QUESTIONS = 20
NUM_POLITICAL_QUESTIONS = 20
EXPECTED_TOTAL_QUESTIONS = NUM_ECONOMIC_QUESTIONS + NUM_SOCIAL_QUESTIONS + NUM_POLITICAL_QUESTIONS
SHORT_TEST_SIZE = 24 # Expected number for short test

try:
    party_answers_df = pd.read_csv(CSV_FILE)
    required_cols = ["Pergunta", "Multiplicador", "Curto"]
    missing_req_cols = [col for col in required_cols if col not in party_answers_df.columns]
    if missing_req_cols: st.error(f"Erro: Coluna(s) necessária(s) não encontrada(s): {', '.join(missing_req_cols)}"); st.stop()

    party_answers_df.set_index("Pergunta", inplace=True)
    multipliers = party_answers_df['Multiplicador']
    is_short_question_col = party_answers_df['Curto']

    if not multipliers.isin([1, -1]).all(): st.warning("Atenção: 'Multiplicador' contém valores inválidos.")

    try:
        short_questions_indices = pd.to_numeric(is_short_question_col, errors='coerce') == 1
        short_questions_list = party_answers_df[short_questions_indices].index.tolist()
        # Allow flexibility, just check if list is non-empty
        can_run_short_test = bool(short_questions_list)
        if len(short_questions_list) != SHORT_TEST_SIZE and can_run_short_test : st.warning(f"Atenção: Encontradas {len(short_questions_list)} perguntas curtas, esperado {SHORT_TEST_SIZE}.")
        if not can_run_short_test: st.error("Erro: Nenhuma pergunta para teste curto (coluna 'Curto').")
    except Exception as e: st.error(f"Erro ao processar coluna 'Curto': {e}"); short_questions_list = []; can_run_short_test = False

    party_answers = party_answers_df.drop(columns=['Multiplicador', 'Curto'], errors='ignore')

except FileNotFoundError: st.error(f"Erro: Ficheiro '{CSV_FILE}' não encontrado."); st.stop()
except Exception as e: st.error(f"Erro ao ler ou processar CSV: {e}"); st.stop()

questions = list(party_answers.index)
TOTAL_QUESTIONS_IN_FILE = len(questions)

if TOTAL_QUESTIONS_IN_FILE < EXPECTED_TOTAL_QUESTIONS: st.warning(f"Atenção: Ficheiro tem {TOTAL_QUESTIONS_IN_FILE} perguntas, esperado {EXPECTED_TOTAL_QUESTIONS}.")

# Define parties and URLs
defined_parties = {
    "AD": "https://ad2024.pt/", "ADN": "https://adn.com.pt/", "BE": "https://www.bloco.org/",
    "Chega": "https://partidochega.pt/", "IL": "https://iniciativaliberal.pt/", "JPP": "https://juntospelopovo.pt/",
    "Livre": "https://partidolivre.pt/", "Nova Direita": "https://novadireita.pt/", "PAN": "https://2024.pan.com.pt/",
    "CDU": "https://www.cdu.pt/", "PCTP/MRPP": "https://www.pctpmrpp.com/", "PS": "https://ps.pt/",
    "RIR": "https://partido-rir.pt/", "Volt": "https://voltportugal.org/",
}
valid_parties_in_csv = [p for p in defined_parties if p in party_answers.columns]
missing_parties = [p for p in defined_parties if p not in party_answers.columns]

if missing_parties: st.warning(f"Partidos definidos mas não encontrados no CSV: {', '.join(missing_parties)}")
if not valid_parties_in_csv: st.error("Erro: Nenhum partido definido encontrado no CSV."); st.stop()

party_answers = party_answers[valid_parties_in_csv]
political_parties = {p: url for p, url in defined_parties.items() if p in valid_parties_in_csv}
party_color_map = {p: color for p, color in party_color_map.items() if p in valid_parties_in_csv}

# **MODIFIED**: Expanded dictionary with detailed party information
# Information based on general knowledge and limited search up to April 2025. Subject to change/interpretation.
party_details = {
    "PS": {
        "partido": "Partido Socialista",
        "lider": "Pedro Nuno Santos (Secretário-Geral)", "fundacao": "19 de abril de 1973",
        "espectro": "Centro-esquerda",
        "ideologias": "Social-democracia, Europeísmo",
        "prioridades": "Reforço do Estado Social (SNS, Educação), Redistribuição de Rendimentos, Europeísmo",
        "descricao": "Principal partido de centro-esquerda em Portugal, defensor do estado social e membro do Partido Socialista Europeu. Procura equilibrar políticas sociais com crescimento económico sustentável.",
        "programa_url": "https://ps.pt/programa/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Partido_Socialista_(Portugal)"
    },
    "AD": {
        "partido": "Aliança Democrática - Coligação PPD-PSD/CDS-PP",
        "lider": "Luís Montenegro (Presidente PPD/PSD)", "fundacao": "PPD/PSD: 6 de maio de 1974 (Coligação AD reeditada em 2023)",
        "espectro": "Centro-direita",
        "ideologias": "Conservadorismo Liberal, Democracia Cristã, Liberalismo Económico",
        "prioridades": "Redução de Impostos (IRS/IRC), Manutenção do Estado Social, Crescimento Económico, Controlo da Dívida Pública",
        "descricao": "Coligação de centro-direita liderada pelo Partido Social Democrata (PPD/PSD), integrando também o CDS-PP. Defende uma economia de mercado com responsabilidade social, reformas para aumentar a competitividade e a estabilidade governativa.",
        "programa_url": "https://ad2025.pt/programa-eleitoral/",
        "wiki_url": "https://pt.wikipedia.org/wiki/AD_%E2%80%94_ALIAN%C3%87A_DEMOCR%C3%81TICA_(2024-Presente)"
    },
    "Livre": {
        "partido": "Livre",        
        "lider": "Rui Tavares, Isabel Mendes Lopes (Porta-vozes)", "fundacao": "2014",
        "espectro": "Esquerda",
        "ideologias": "Socialismo, Progressismo, Ecologia, Europeísmo, Direitos das Minorias",
        "prioridades": "Redistribuição de Rendimentos, Combate às Alterações Climáticas, Direitos de Minorias, Habitação, Rendimento Básico Incondicional (RBI)",
        "descricao": "Partido de esquerda com forte ênfase na ecologia, direitos humanos, aprofundamento democrático e maior integração europeia. Defende políticas sociais inclusivas e um modelo económico socialista e com enfâse na sustentabilidade. Conhecido pelo seu modelo de liderança com porta-vozes rotativos.",
        "programa_url": "https://programa.partidolivre.pt/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Livre_(partido_pol%C3%ADtico)"
    },
    "PAN": {
        "partido": "Pessoas-Animais-Natureza",   
        "lider": "Inês Sousa Real (Porta-Voz)", "fundacao": "2011",
        "espectro": "Centro-esquerda",
        "ideologias": "Ambientalismo, Direitos dos Animais, Humanismo",
        "prioridades": "Proteção Animal e Ambiental, Saúde Única (Humana/Animal/Ambiental), Combate às Alterações Climáticas, Direitos Humanos",
        "descricao": "Partido Pessoas-Animais-Natureza, focado na defesa dos direitos dos animais e na proteção ambiental como eixos centrais. Promove políticas de sustentabilidade, bem-estar animal, preservação dos ecosistemas e economia verde. Geralmente alinha com o centro-esquerda em questões sociais.",
        "programa_url": "https://2024.pan.com.pt/program",
        "wiki_url": "https://pt.wikipedia.org/wiki/Pessoas%E2%80%93Animais%E2%80%93Natureza"
    },
    "IL": {
        "partido": "Iniciativa Liberal",
        "lider": "Rui Rocha (Presidente)", "fundacao": "2017",
        "espectro": "Direita",
        "ideologias": "Liberalismo (Clássico e Económico), Libertarianismo (influências)",
        "prioridades": "Redução de Impostos e Burocracia, Liberdade Económica e Individual, Reforma do Estado, Privatizações",
        "descricao": "Partido liberal que defende uma intervenção limitada do Estado na economia e na sociedade. Propõe a liberalização e desregulação do mercado, privatização da maioria das empresas públicas, impostos significativamente mais baixos e maior liberdade de escolha individual.",
        "programa_url": "https://iniciativaliberal.pt/programas/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Iniciativa_Liberal"
    },
    "BE": {
        "partido": "Bloco de Esquerda",
        "lider": "Mariana Mortágua (Coordenadora)", "fundacao": "1999",
        "espectro": "Extrema-esquerda",
        "ideologias": "Socialismo, Anti-capitalismo, Progressismo, Direitos das Minorias",
        "prioridades": "Reforço dos Serviços Públicos (SNS, Escola), Direitos Laborais, Redistribuição dos rendimentos, Nacionalizações",
        "descricao": "Partido de esquerda radical, crítico do liberalismo e defensor de alternativas socialistas e ecológicas. Resultou da fusão de vários movimentos de esquerda. Forte ênfase nos direitos das minorias e na justiça social.",
        "programa_url": "https://www.bloco.org/programa",
        "wiki_url": "https://pt.wikipedia.org/wiki/Bloco_de_Esquerda"
    },
    "CDU": {
        "partido": "Coligação Democrática Unitária (Partido Cominista Português + Partido Ecologista Os Verdes)",
        "lider": "Paulo Raimundo (Secretário-Geral PCP)", "fundacao": "PCP: 1921 (Coligação CDU: 1987)",
        "espectro": "Extrema-esquerda",
        "ideologias": "Comunismo (Marxismo-Leninismo - PCP), Ecossocialismo (PEV)",
        "prioridades": "Direitos dos Trabalhadores, Serviços Públicos Universais e Gratuitos, Nacionalizações, Soberania Nacional, Oposição à NATO e União Europeia",
        "descricao": "Aliança permanente entre o Partido Comunista Português (PCP) e o Partido Ecologista \"Os Verdes\" (PEV). Defende os interesses dos trabalhadores, o reforço do sector público e a soberania nacional. O PCP mantém uma linha marxista-leninista.",
        "programa_url": "https://www.cdu.pt/legislativas2025/compromisso-eleitoral-do-pcp",
        "wiki_url": "https://pt.wikipedia.org/wiki/Coliga%C3%A7%C3%A3o_Democr%C3%A1tica_Unit%C3%A1ria"
    },
    "Chega": {
        "partido": "Chega",        
        "lider": "André Ventura (Presidente)", "fundacao": "2019",
        "espectro": "Extrema-direita",
        "ideologias": " Conservadorismo cristão, Nacionalismo, Anti-imigração, Anti-corrupção",
        "prioridades": "Diminuição da Imigração, Combate à Corrupção e ao Sistema, Reforço da Segurança e Autoridade do Estado, Redução de Impostos",
        "descricao": "Partido de direita radical com discurso centrado na defesa da identidade nacional, segurança, críticas ao sistema político e posições anti-imigração. Defende valores conservadores, nacionalistas e liberalismo económico.",
        "programa_url": "https://partidochega.pt/programa/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Chega_(partido_pol%C3%ADtico)"
    },
     "RIR": {
        "partido": "Reagir-Incluir-Reciclar", 
        "lider": "Márcia Henriques (Presidente)", "fundacao": "2019",
        "espectro": "Centro",
        "ideologias": "Centrismo, Humanismo, Reformismo, Descentralização, Ecologia",
        "prioridades": "Reforma do sistema político/justiça, Transparência, Combate à corrupção",
        "descricao": "Apresenta-se como alternativa aos partidos de centro esquerda e centro direita, com foco na reforma do sistema de justiça e político de forma a aumentar a transparência e a representatividade democrática. Adota posições geralmente moderadas noutras áreas.",
        "programa_url": "https://partido-rir.pt/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Reagir_Incluir_Reciclar"
    },
    "JPP": {
        "partido": "Juntos Pelo Povo",  
        "lider": "Lina Pereira (Presidente), Élvio Sousa (Secretário Geral)", "fundacao": "2015",
        "espectro": "Centro (Regionalista)",
        "ideologias": "Regionalismo (Madeira), Social-democracia (local), Liberalismo, Autonomismo",
        "prioridades": "Interesses da Madeira, Regionalismo, Centrismo, Transparência",
        "descricao": "Partido com forte base na Madeira, focado na defesa dos interesses da região e na luta por maior autonomia. Adota posições pragmáticas e de centro localmente.",
        "programa_url": "https://juntospelopovo.pt/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Juntos_pelo_Povo"
    },
    "ADN": {
        "partido": "Alternativa Democrática Nacional",  
        "lider": "Bruno Fialho (Presidente)", "fundacao": "2015 (como PDR), 2021 (ADN)",
        "espectro": "Extrema-direita",
        "ideologias": "Conservadorismo, Nacionalismo, Anti-globalismo, Anti-establishment",
        "prioridades": "Combate à corrupção, Redução do Estado, Soberania Nacional, Anti-vacinas , Oposição a 'agendas globais'",
        "descricao": "Anterior Partido Democrático Republicano. Partido conservador e nacionalista, muito crítico do sistema político atual, do papel do estado na sociedade, de organizações/agendas internacionais (Organizaçãp Mundial da Saúde, clima, etc.) e de consensos científicos.",
        "programa_url": "https://adn.com.pt/programa-eleitoral/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Alternativa_Democr%C3%A1tica_Nacional"
    },
    "PCTP/MRPP": {
        "partido": "Partido Comunista dos Trabalhadores Portugueses",  
        "lider": "Liderança coletiva", "fundacao": "1970 (MRPP), 1976 (PCTP/MRPP)",
        "espectro": "Extrema-esquerda",
        "ideologias": "Comunismo, Marxismo-Leninismo, Maoismo",
        "prioridades": "Revolução socialista, Ditadura do proletariado, Anti-imperialismo",
        "descricao": "Partido de linha maoista, mantém discurso revolucionário clássico que advoga a nacionalização dos meios de produção.",
        "programa_url": "https://www.pctpmrpp.com/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Partido_Comunista_dos_Trabalhadores_Portugueses"
    },
    "Nova Direita": {
        "partido": "Nova Direita",  
        "lider": "Ossanda Liber (Presidente)", "fundacao": "2023",
        "espectro": "Direita",
        "ideologias": "Conservadorismo cristão, Anti-imigração, Liberalismo económico, Nacionalismo",
        "prioridades": "Diminuição da imigração, Redução de impostos, Segurança, Defesa da família tradicional, Controlo da Dívida Pública",
        "descricao": "Partido fundado por dissidentes do CDS-PP. Apresenta-se como conservador nos costumes e liberal na economia, defendendo valores da direita.",
        "programa_url": "https://novadireita.pt/legislativas-2025/",
        "wiki_url": "https://pt.wikipedia.org/wiki/Nova_Direita_(Portugal)"
    },
    "Volt": {
        "partido": "Volt Portugal",  
        "lider": "Duarte Costa, Inês Bravo Figueiredo (Co-Presidentes)", "fundacao": "2020",
        "espectro": "Centro",
        "ideologias": "Liberalismo Social, Progressismo, Federalismo Europeu, Ecologia",
        "prioridades": "Reforma da UE, Transição digital e climática, Políticas sociais pragmáticas, Direitos Humanos",
        "descricao": "Secção portuguesa do movimento pan-europeu Volt Europa. Defende uma economia de mercado livre complementada com um estado social forte com base em políticas progressistas e baseadas em evidência científica e em melhores práticas. Defende uma União Europeia mais integrada e democrática.",
        "programa_url": "https://voltportugal.org/programa",
        "wiki_url": "https://pt.wikipedia.org/wiki/Volt_Portugal"
    }
}
# Filter details based on valid parties found in CSV
party_details = {p: details for p, details in party_details.items() if p in valid_parties_in_csv}


if 'mode' not in st.session_state: st.session_state.mode = 'intro'
if 'idx' not in st.session_state: st.session_state.idx = -1
if 'answers' not in st.session_state: st.session_state.answers = {}

# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------

# (show_intro, show_question, show_midpoint_choice, calculate_compass_scores unchanged)
def show_intro():
    """Shows the intro page with test length choice."""
    st.title("Votímetro")
    st.write("Bem-vindo! Este teste visa avaliar o seu posicionamento político e compará-lo com os partidos portugueses em 2025. O utilizador será confrontado com afirmações e será pedido para escolher qual o nível de concordância. ")
    st.write("")
    st.write("Os resultados mostram o grau de semelhança das resposta do utilizador em relação a cada partido, medido pela soma dos desvios absolutos em todas as respostas do teste, bem como o posicionamento relativamente aos vários partidos políticos portugueses em 3 eixos.")
    st.write("")
    # Use len(short_questions_list) if available, else SHORT_TEST_SIZE as fallback text
    short_q_count = len(short_questions_list) if can_run_short_test else SHORT_TEST_SIZE
    st.write(f"Pode optar por fazer um teste **curto de {short_q_count} perguntas** (resultados mais rápidos mas menos precisos) ou o teste **completo de {len(questions)} perguntas** (resultados mais fiáveis).")
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='start-btn'>", unsafe_allow_html=True)
        if st.button(f"Iniciar Teste Curto ({short_q_count} Perguntas)", key="start_short", disabled=not can_run_short_test):
            st.session_state.mode = 'short'; st.session_state.idx = 0; st.session_state.answers = {}; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        if not can_run_short_test: st.caption("Opção indisponível.")
    with col2:
        st.markdown("<div class='start-btn'>", unsafe_allow_html=True)
        if st.button(f"Iniciar Teste Completo ({len(questions)} Perguntas)", key="start_full"):
            st.session_state.mode = 'full'; st.session_state.idx = 0; st.session_state.answers = {}; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.write("---")
    st.markdown("**Partidos incluídos:** " + " | ".join([f"[{p}]({url})" for p, url in political_parties.items()]))
    st.caption("O teste inclui os partidos que tiveram mais do que 7000 votos nas eleições legislativas de 2024 (mínimo de assinaturas para a formação de um partido político em Portugal). ")   
    st.caption("As afirmações que compõem o teste visam avaliar a posição relativamente a valores políticos abstractos e intemporais, não a questões especificas da realidade portuguesa em 2025. As afirmações cobrem 3 eixos:")
    st.caption("")
    st.caption("**Eixo Económico**: Mede o grau de intervenção geral do Estado na Economia. Espectro Esquerda-Direita.")
    st.caption("**Eixo Social**: Mede o grau de abertura a mudanças sociais. Espectro Conservador-Progressista.")
    st.caption("**Eixo Político**: Mede o grau de liberalismo político a nível de política interna e externa. Espectro Autoritário/Nacionalista-Liberal/Globalista")    
    st.caption("")
    st.caption("As respostas dos partidos são baseadas na avaliação da equipa que elaborou o teste tendo em conta os conteúdos dos mais recententes programas, posições públicas passadas, e a ideologia de cada partido. A equipa encontra-se disponível para ajustar as respostas de cada partido, caso os partidos entrem em contacto (miguelptcosta1995+votimetro@gmail.com).")

def show_question(current_idx, question_list, total_questions_in_mode):
    """Shows the current question, answer buttons, skip, and back buttons."""
    if not (0 <= current_idx < len(question_list)): st.error("Erro interno: Índice de pergunta inválido."); st.session_state.mode = 'intro'; st.session_state.idx = -1; st.rerun(); return
    question_text = question_list[current_idx]
    st.header(f"Pergunta {current_idx + 1} de {total_questions_in_mode}")
    st.subheader(question_text)
    st.write("Qual a sua posição sobre esta afirmação?")
    options = {"Discordo totalmente": -2, "Discordo parcialmente": -1, "Neutro ou Ambíguo": 0, "Concordo parcialmente": 1, "Concordo totalmente": 2}
    button_pressed_type = None
    next_idx = current_idx + 1
    cols = st.columns(5)
    for i, (label, value) in enumerate(options.items()):
        with cols[i]:
            if st.button(label, key=f"q{current_idx}_opt_{i}"):
                st.session_state.answers[question_text] = value; st.session_state.idx = next_idx; button_pressed_type = 'answer'; break

    button_below_container = st.container()
    with button_below_container:
        st.markdown("<div class='skip-btn-wrapper'>", unsafe_allow_html=True)
        # **MODIFIED**: Added type="primary"
        if st.button("Sem opinião", key=f"q{current_idx}_skip", use_container_width=True, type="tertiary"):
            st.session_state.answers.pop(question_text, None); st.session_state.idx = next_idx; button_pressed_type = 'skip'
        st.markdown("</div>", unsafe_allow_html=True)

        if current_idx > 0:
            st.markdown("<div class='recuar-btn-wrapper'>", unsafe_allow_html=True)
            # **MODIFIED**: Added type="primary"
            if st.button("Recuar", key=f"q{current_idx}_back", use_container_width=True, type="tertiary"):
                st.session_state.idx -= 1; button_pressed_type = 'back'
            st.markdown("</div>", unsafe_allow_html=True)

    if button_pressed_type in ['answer', 'skip']:
        if st.session_state.mode == 'short' and st.session_state.idx == len(short_questions_list): st.session_state.mode = 'midpoint'; st.rerun()
        elif st.session_state.mode == 'full' and st.session_state.idx == len(questions): st.session_state.mode = 'results'; st.rerun()
        elif st.session_state.mode not in ['midpoint', 'results']: st.rerun()
    elif button_pressed_type == 'back': st.rerun()

def show_midpoint_choice():
    """Displays screen after short test, asking user to continue or see results."""
    st.header(f"Teste Curto ({len(short_questions_list)} Perguntas) Concluído!")
    st.write("Pode ver já os seus resultados (baseados nestas perguntas, menos precisos) ou continuar o teste para responder a todas as perguntas e obter resultados mais fiáveis.")
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
         st.markdown("<div class='midpoint-btn'>", unsafe_allow_html=True)
         if st.button(f"Ver Resultados ({len(short_questions_list)} Perguntas)", key="results_short"): st.session_state.mode = 'results'; st.rerun()
         st.markdown("</div>", unsafe_allow_html=True)
    with col2:
         st.markdown("<div class='midpoint-btn'>", unsafe_allow_html=True)
         if st.button(f"Continuar Teste ({len(questions)} Perguntas)", key="continue_full"): st.session_state.mode = 'full'; st.rerun()
         st.markdown("</div>", unsafe_allow_html=True)

def calculate_compass_scores(entity_answers, all_questions_list, question_multipliers):
    """ Calculates Economic, Social, and Political scores (-1 to 1) using multipliers. """
    scores = {'Economic': 0.0, 'Social': 0.0, 'Political': 0.0}
    econ_end = min(len(all_questions_list), NUM_ECONOMIC_QUESTIONS)
    social_end = min(len(all_questions_list), NUM_ECONOMIC_QUESTIONS + NUM_SOCIAL_QUESTIONS)
    political_end = min(len(all_questions_list), EXPECTED_TOTAL_QUESTIONS)
    axis_definitions = {
        'Economic': all_questions_list[0:econ_end],
        'Social': all_questions_list[NUM_ECONOMIC_QUESTIONS:social_end],
        'Political': all_questions_list[NUM_ECONOMIC_QUESTIONS + NUM_SOCIAL_QUESTIONS : political_end]
    }
    for axis_name, question_texts in axis_definitions.items():
        if question_texts:
            valid_answers = entity_answers.reindex(question_texts).dropna()
            num_answered = len(valid_answers)
            if num_answered > 0:
                relevant_multipliers = question_multipliers.reindex(valid_answers.index)
                weighted_score_sum = (valid_answers * relevant_multipliers).sum()
                normalized_score = weighted_score_sum / (num_answered * 2.0)
                scores[axis_name] = max(-1.0, min(1.0, normalized_score))
    return scores['Economic'], scores['Social'], scores['Political']


def show_results():
    """Shows the results page: affinity chart, compass chart, party info, share buttons."""
    st.success("Teste concluído!")
    perguntas_respondidas_list = list(st.session_state.answers.keys())
    num_perguntas_respondidas = len(perguntas_respondidas_list)

    if not perguntas_respondidas_list:
        st.warning("Não respondeu a nenhuma pergunta.")
        if st.button("Reiniciar Teste"): st.session_state.mode = 'intro'; st.session_state.idx = -1; st.session_state.answers = {}; st.rerun()
        return

    is_short_result = can_run_short_test and (num_perguntas_respondidas == len(short_questions_list)) and (len(short_questions_list) < len(questions))
    is_full_result = (num_perguntas_respondidas == len(questions))
    if is_short_result : st.info(f"Resultados baseados no teste curto de {num_perguntas_respondidas} perguntas.")
    elif is_full_result: st.info(f"Resultados baseados no teste completo de {num_perguntas_respondidas} perguntas.")
    else: st.info(f"Resultados baseados em {num_perguntas_respondidas} perguntas respondidas.")

    # --- 1. Affinity Score Calculation & Chart ---
    st.header("Percentagem de Concordância com os Partidos Portugueses")
    # (Calculation and chart code as before)
    respostas_partidos_filtradas = party_answers.loc[perguntas_respondidas_list]
    user_answers_series = pd.Series(st.session_state.answers).reindex(perguntas_respondidas_list)
    total_distances = {}
    for party_name in political_parties.keys():
        if party_name in respostas_partidos_filtradas.columns:
            diff = abs(respostas_partidos_filtradas[party_name] - user_answers_series)
            total_distances[party_name] = diff.sum()
    total_distances_series = pd.Series(total_distances)
    max_dist = 4 * num_perguntas_respondidas if num_perguntas_respondidas > 0 else 1
    affinity = (1 - (total_distances_series / max_dist)).clip(lower=0.0, upper=1.0)
    affinity.sort_values(ascending=False, inplace=True)
    affinity_df = affinity.reset_index(); affinity_df.columns = ['Partido', 'Concordância']
    color_domain = affinity_df['Partido'].tolist()
    color_range = [party_color_map.get(p, "#CCCCCC") for p in color_domain]
    affinity_chart = alt.Chart(affinity_df).mark_bar().encode(
         x=alt.X('Concordância', axis=alt.Axis(format='%', title="Percentagem de Concordância", grid=False)),
         y=alt.Y('Partido', sort='-x', title="Partido", axis=alt.Axis(labelLimit=200)),
         color=alt.Color('Partido', scale=alt.Scale(domain=color_domain, range=color_range), legend=None),
         tooltip=['Partido', alt.Tooltip('Concordância', format='.1%')]
     ).properties(background='transparent')
    st.altair_chart(affinity_chart, use_container_width=True)
    st.write("O gráfico acima mostra a concordância geral com base em todas as suas respostas. Para cada afirmação, uma resposta mais distante do utilizador em relação à resposta de um determinado partido, diminui a semelhança com esse partido.")
    st.caption("Nota: O teste dá o mesmo peso a todas as afirmações, o que normalmente não reflete as preferências dos eleitores. Assim, é útil considerar não apenas o partido com maior percentagem de semelhança, mas também os partidos com percentagens próximas. ")    
    st.write("---")

    # --- 2. Political Compass Calculation & Chart ---
    st.header("Bússola Política")
    # (Calculation and chart code as before)
    compass_data = []
    full_user_answers_series = pd.Series(st.session_state.answers)
    user_econ, user_social, user_political = calculate_compass_scores(full_user_answers_series, questions, multipliers)
    compass_data.append({"Entidade": "Você", "Eixo Económico": user_econ, "Eixo Social": user_social, "Eixo Político": user_political})
    for party_name in political_parties.keys():
        if party_name in party_answers.columns:
            party_col_full = party_answers[party_name]
            p_econ, p_social, p_political = calculate_compass_scores(party_col_full, questions, multipliers)
            compass_data.append({"Entidade": party_name, "Eixo Económico": p_econ, "Eixo Social": p_social, "Eixo Político": p_political})
    compass_df = pd.DataFrame(compass_data)

    if not compass_df.empty:
        origin_lines = pd.DataFrame({'zero': [0]})
        vline = alt.Chart(origin_lines).mark_rule(strokeDash=[3,3], color='grey', size=0.5).encode(x='zero:Q')
        hline = alt.Chart(origin_lines).mark_rule(strokeDash=[3,3], color='grey', size=0.5).encode(y='zero:Q')
        base = alt.Chart(compass_df).encode(
            x=alt.X('Eixo Económico', scale=alt.Scale(domain=[-1.1, 1.1]), axis=alt.Axis(title='Económico (Esquerda <-> Direita)', grid=False, format=".1f")),
            y=alt.Y('Eixo Social', scale=alt.Scale(domain=[-1.1, 1.1]), axis=alt.Axis(title='Social (Conservador <-> Progressista)', grid=False, format=".1f"))
        )
        color_scale = alt.Scale(domain=[-1, 0, 1], range=['#FF0000', '#808080', '#FFFF00'])
        points = base.mark_point(size=120, filled=True, opacity=0.9).encode(
            color=alt.Color('Eixo Político', scale=color_scale, legend=alt.Legend(title="Eixo Político", orient="top", titleOrient="left", gradientLength=200, format=".1f")),
            tooltip=['Entidade', alt.Tooltip('Eixo Económico', format='.2f'), alt.Tooltip('Eixo Social', format='.2f'), alt.Tooltip('Eixo Político', format='.2f', title="Político (Aut/Lib)")],
            shape=alt.condition(alt.datum.Entidade == 'Você', alt.value('triangle'), alt.value('circle'))
        )
        text = base.mark_text(align='left', baseline='middle', dx=9, fontSize=12, fontWeight='bold').encode(text='Entidade', color=alt.value('#FFFFFF'))
        compass_chart = (vline + hline + points + text).properties(background='transparent').interactive()
        st.altair_chart(compass_chart, use_container_width=True)
        st.write("""
            **Como interpretar a Bússola Política:**
            * **Posição Horizontal (Eixo X):** Eixo **Económico**. Esquerda (-1) vs Direita (+1).
            * **Posição Vertical (Eixo Y):** Eixo **Social**. Conservador (-1) vs Progressista (+1).
            * **Côr:** Eixo **Político**. Vermelho (Autoritário/Nacionalista, -1) -> Cinzento (Neutro, 0) -> Amarelo (Liberal/Globalista, +1).

            A sua posição ("Você") é marcada com um triângulo (▲). As posições são calculadas com base nas suas respostas.
            """ # Updated explanation for marker and overlap acknowledgement
        )
        st.caption("Nota: Se as etiquetas se sobrepuserem, use o zoom ou passe o rato.")
    else: st.warning("Não foi possível gerar a Bússola Política.")
    st.write("---")


    # --- 3. Expandable Party Information Section (MODIFIED) ---
    st.subheader("Descobre mais sobre os Partidos")
    st.caption("Classificações de espectro, ideologias e prioridades são subjectivas e identificadas com ajuda de Inteligência Artificial (ChatGPT).") # Add disclaimer

    sorted_party_names = sorted(political_parties.keys())
    for party_name in sorted_party_names:
        with st.expander(f"{party_name}"):
            # Get details safely, providing defaults if missing
            details = party_details.get(party_name, {})
            official_url = political_parties.get(party_name, "#")

            # Display new fields + existing fields
            st.markdown(f"**Partido/Coligação:** {details.get('partido', 'N/D')}")            
            st.markdown(f"**Líder(es) (ref. Abril 2025):** {details.get('lider', 'N/D')}")
            st.markdown(f"**Fundação:** {details.get('fundacao', 'N/D')}")
            st.markdown(f"**Espectro Político:** {details.get('espectro', 'N/D')}")
            st.markdown(f"**Ideologias Associadas:** {details.get('ideologias', 'N/D')}")
            st.markdown(f"**Prioridades:** {details.get('prioridades', 'N/D')}")
            st.markdown(f"**Descrição:** {details.get('descricao', 'N/D')}") # Use updated, longer description
            st.markdown(f"**Links:**")
            st.markdown(f"- [Site Oficial]({official_url})")

            # Handle program link display
            programa_url = details.get('programa_url', '#')
            if "URL_PROGRAMA" in programa_url or programa_url == '#': # Check for placeholder or missing link
                 programa_text = f"[Programa Eleitoral (Ver site oficial)]({official_url})"
            else:
                 programa_text = f"[Programa Eleitoral]({programa_url})"
            st.markdown(f"- {programa_text}")

            # Wikipedia link
            st.markdown(f"- [Página Wikipedia]({details.get('wiki_url', '#')})")

    # --- 4. Share Results Section ---
    st.write("---") # Separator before sharing
    st.subheader("Partilhar Resultados")
    # (Sharing code remains the same)
    top_party = affinity_df.iloc[0]['Partido'] if not affinity_df.empty else "Nenhum"
    top_affinity = affinity_df.iloc[0]['Concordância'] if not affinity_df.empty else 0
    share_text_base = f"Fiz o teste Paradigma Político! O meu partido mais próximo foi {top_party} ({top_affinity:.0%}). Descobre a tua posição:"
    share_text_encoded = urllib.parse.quote_plus(f"{share_text_base} {APP_URL}")
    share_text_twitter = urllib.parse.quote_plus(f"{share_text_base}")
    app_url_encoded = urllib.parse.quote_plus(APP_URL)
    hashtags = "ParadigmaPoliticoPT,PoliticaPortuguesa"
    facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={app_url_encoded}"
    x_url = f"https://twitter.com/intent/tweet?url={app_url_encoded}&text={share_text_twitter}&hashtags={hashtags}"
    whatsapp_url = f"https://wa.me/?text={share_text_encoded}"
    email_subject = urllib.parse.quote_plus("O meu resultado no Paradigma Político")
    email_url = f"mailto:?subject={email_subject}&body={share_text_encoded}"
    st.markdown("<div class='share-button-container'>", unsafe_allow_html=True)
    st.markdown(f'<a href="{facebook_url}" target="_blank" class="share-btn share-btn-facebook">Facebook</a>', unsafe_allow_html=True)
    st.markdown(f'<a href="{x_url}" target="_blank" class="share-btn share-btn-x">X (Twitter)</a>', unsafe_allow_html=True)
    st.markdown(f'<a href="{whatsapp_url}" target="_blank" class="share-btn share-btn-whatsapp">WhatsApp</a>', unsafe_allow_html=True)
    st.markdown(f'<a href="{email_url}" target="_blank" class="share-btn share-btn-email">Email</a>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


    # --- Footer / Restart Button ---
    st.write("---")
    # **MODIFIED**: Added wrapper and use_container_width=True
    st.markdown("<div class='restart-btn-wrapper'>", unsafe_allow_html=True)
    if st.button("Reiniciar Teste", use_container_width=True, key="restart_test_results", type="tertiary"): # Added key for clarity
        st.session_state.mode = 'intro'; st.session_state.idx = -1; st.session_state.answers = {}; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# Main Application Flow (Using Mode State)
# -------------------------------------------------------------------------
# (Main flow logic remains the same)
current_mode = st.session_state.get('mode', 'intro')

if current_mode == 'intro':
    show_intro()
elif current_mode == 'short':
    show_question(st.session_state.idx, short_questions_list, len(short_questions_list))
elif current_mode == 'full':
     total_q_display = len(questions)
     show_question(st.session_state.idx, questions, total_q_display)
elif current_mode == 'midpoint':
    show_midpoint_choice()
elif current_mode == 'results':
    show_results()
else: # Fallback
    st.error("Erro: Estado inválido. A reiniciar."); st.session_state.mode = 'intro'; st.session_state.idx = -1; st.session_state.answers = {}; st.rerun()