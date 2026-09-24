# -*- coding: utf-8 -*-
"""Simple translation system, independent of QGIS's own locale.

Qt's standard mechanism (.ts/.qm files + QTranslator) follows the QGIS
installation's locale, which has no guaranteed relation to the country
selected in the plugin or the language the user actually wants. This
module implements its own language selector instead.

All UI text is written in Portuguese in the code — it's both the
default language and the lookup key. TRANSLATIONS holds, per
language, a {portuguese text: translated text} dict. Translator.tr()
returns the translation if one exists, otherwise the original
Portuguese text — so a missing translation never breaks anything,
and strings can be migrated one at a time.

Current coverage: the most visible UI elements (header, tabs, the
full Filters tab, main buttons, login messages). The rest of the
plugin still falls back to Portuguese until added to the dict.
"""

LANGUAGES = (
    ("pt", "Português"),
    ("es", "Español"),
    ("en", "English"),
)

LANGUAGE_NAMES = dict(LANGUAGES)

# Suggested initial language by country — only the default when switching
# country; the user can freely change it via the plugin's language
# selector, and that manual choice is respected on subsequent country
# switches (see main_dialog.py, update_platform/on_language_changed).
DEFAULT_LANGUAGE_BY_COUNTRY = {
    "BR": "pt",
    "BO": "es",
    "CO": "es",
    "PE": "es",
    "ID": "en",
}

# Suffix for the LEIA-ME/README file generated in layer exports with
# territorial crossings (see write_crossings_readme in main_dialog.py) —
# both the filename and its content must follow the selected language,
# not just the UI text. Deliberately free of accents or special
# characters, to avoid filename issues on older filesystems or network
# drives.
README_FILENAME_SUFFIX = {
    "pt": "LEIA-ME",
    "es": "LEAME",
    "en": "README",
}

CROSSINGS_README_TEXT = {
    "pt": (
        "LEIA-ME — ARQUIVOS EXPORTADOS PELO MAPBIOMAS ALERTA OFICIAL\n"
        "================================================================\n\n"
        "Este export tem mais de um arquivo/tabela porque a divisão de "
        "área por território (Unidade de Conservação, Terra Indígena, "
        "Assentamento, Quilombo, Reserva da Biosfera, Geoparque, APP, "
        "Reserva Legal etc.) é organizada em DOIS formatos diferentes, "
        "um para cada uso:\n\n"
        "1) TABELA PRINCIPAL — 1 linha por ALERTA\n"
        "   Cada alerta aparece uma única vez, com sua geometria e seus\n"
        "   atributos (área, datas, bioma/estado/município...). A "
        "divisão\n"
        "   por território, quando existe, vem dentro de colunas com "
        "texto\n"
        "   em formato JSON (ex.: {\"Nome do território\":área_em_ha}).\n\n"
        "2) TABELA/ARQUIVO DE CRUZAMENTOS — 1 linha por ALERTA × "
        "TERRITÓRIO\n"
        "   Aqui o mesmo dado da coluna JSON acima é repetido em "
        "formato\n"
        "   longo: cada território que um alerta cruza vira uma linha "
        "própria,\n"
        "   com o código do alerta, a categoria (ex.: \"UnidConserv\"), "
        "o nome\n"
        "   do território e a área em hectares. Por isso esta tabela "
        "SEMPRE\n"
        "   tem muito mais linhas que a tabela principal: um alerta que "
        "cruza\n"
        "   3 territórios diferentes gera 3 linhas aqui, mas continua "
        "sendo\n"
        "   1 único alerta na tabela principal. Isso não é duplicação "
        "nem\n"
        "   erro — é o mesmo dado reorganizado para ser fácil de somar, "
        "filtrar\n"
        "   ou cruzar com outras planilhas, sem precisar interpretar "
        "o JSON.\n\n"
        "COMO RELACIONAR AS DUAS TABELAS\n"
        "   Use a coluna \"CodeAlerta\" (código do alerta) para juntar "
        "as duas —\n"
        "   é a mesma chave nas duas tabelas.\n\n"
        "ATENÇÃO SOBRE SOBREPOSIÇÃO\n"
        "   Para Unidade de Conservação, Terra Indígena, Assentamento, "
        "Quilombo,\n"
        "   Reserva da Biosfera, Geoparque, APP e Reserva Legal, a "
        "própria\n"
        "   plataforma MapBiomas Alerta calcula a área de cada "
        "declaração\n"
        "   individualmente, SEM remover sobreposições entre "
        "declarações\n"
        "   diferentes. Ou seja, se dois territórios cruzados se "
        "sobrepõem\n"
        "   entre si, a soma das áreas individuais pode ultrapassar a "
        "área\n"
        "   total do alerta — isso é esperado e não indica erro. Já "
        "para\n"
        "   Bioma, Estado e Município, que não se sobrepõem entre si, "
        "a soma\n"
        "   das áreas individuais sempre corresponde à área total do "
        "alerta."
    ),
    "es": (
        "LÉAME — ARCHIVOS EXPORTADOS POR MAPBIOMAS ALERTA OFICIAL\n"
        "================================================================\n\n"
        "Esta exportación tiene más de un archivo/tabla porque la "
        "división de área por territorio (Área Protegida, Territorio "
        "Indígena, Asentamiento, Quilombo, Reserva de la Biosfera, "
        "Geoparque, APP, Reserva Legal etc.) está organizada en DOS "
        "formatos diferentes, uno para cada uso:\n\n"
        "1) TABLA PRINCIPAL — 1 línea por ALERTA\n"
        "   Cada alerta aparece una única vez, con su geometría y sus\n"
        "   atributos (área, fechas, bioma/departamento/municipio...). "
        "La división\n"
        "   por territorio, cuando existe, viene dentro de columnas con "
        "texto\n"
        "   en formato JSON (ej.: {\"Nombre del territorio\":área_en_ha}"
        ").\n\n"
        "2) TABLA/ARCHIVO DE CRUCES — 1 línea por ALERTA × TERRITORIO\n"
        "   Aquí el mismo dato de la columna JSON de arriba se repite "
        "en formato\n"
        "   largo: cada territorio que una alerta cruza se convierte "
        "en una línea\n"
        "   propia, con el código de la alerta, la categoría (ej.: "
        "\"UnidConserv\"),\n"
        "   el nombre del territorio y el área en hectáreas. Por eso "
        "esta tabla\n"
        "   SIEMPRE tiene muchas más líneas que la tabla principal: "
        "una alerta que\n"
        "   cruza 3 territorios diferentes genera 3 líneas aquí, pero "
        "sigue siendo\n"
        "   1 sola alerta en la tabla principal. Esto no es "
        "duplicación ni\n"
        "   error — es el mismo dato reorganizado para ser fácil de "
        "sumar, filtrar\n"
        "   o cruzar con otras planillas, sin necesidad de interpretar "
        "el JSON.\n\n"
        "CÓMO RELACIONAR LAS DOS TABLAS\n"
        "   Use la columna \"CodeAlerta\" (código de la alerta) para "
        "unir las dos —\n"
        "   es la misma clave en las dos tablas.\n\n"
        "ATENCIÓN SOBRE SUPERPOSICIÓN\n"
        "   Para Área Protegida, Territorio Indígena, Asentamiento, "
        "Quilombo,\n"
        "   Reserva de la Biosfera, Geoparque, APP y Reserva Legal, la "
        "propia\n"
        "   plataforma MapBiomas Alerta calcula el área de cada "
        "declaración\n"
        "   individualmente, SIN eliminar superposiciones entre "
        "declaraciones\n"
        "   diferentes. Es decir, si dos territorios cruzados se "
        "superponen\n"
        "   entre sí, la suma de las áreas individuales puede superar "
        "el área\n"
        "   total de la alerta — esto es esperado y no indica un "
        "error. En cambio,\n"
        "   para Bioma, Departamento y Municipio, que no se superponen "
        "entre sí,\n"
        "   la suma de las áreas individuales siempre corresponde al "
        "área total\n"
        "   de la alerta."
    ),
    "en": (
        "README — FILES EXPORTED BY MAPBIOMAS ALERTA OFICIAL\n"
        "================================================================\n\n"
        "This export has more than one file/table because the area "
        "breakdown by territory (Protected Area, Indigenous Land, "
        "Settlement, Quilombo, Biosphere Reserve, Geopark, PPA, Legal "
        "Reserve etc.) is organized in TWO different formats, one for "
        "each use:\n\n"
        "1) MAIN TABLE — 1 row per ALERT\n"
        "   Each alert appears only once, with its geometry and its\n"
        "   attributes (area, dates, biome/state/municipality...). The "
        "breakdown\n"
        "   by territory, when it exists, comes inside columns with "
        "JSON\n"
        "   text (e.g.: {\"Territory name\":area_in_ha}).\n\n"
        "2) CROSSINGS TABLE/FILE — 1 row per ALERT × TERRITORY\n"
        "   Here the same data from the JSON column above is repeated "
        "in long\n"
        "   format: each territory an alert crosses becomes its own "
        "row,\n"
        "   with the alert code, the category (e.g.: \"UnidConserv\"), "
        "the\n"
        "   territory name, and the area in hectares. That's why this "
        "table\n"
        "   ALWAYS has many more rows than the main table: a single "
        "alert\n"
        "   crossing 3 different territories generates 3 rows here, "
        "but it's\n"
        "   still 1 single alert in the main table. This is not "
        "duplication\n"
        "   or an error — it's the same data reorganized to be easy to "
        "sum,\n"
        "   filter, or cross with other spreadsheets, without needing "
        "to\n"
        "   parse the JSON.\n\n"
        "HOW TO RELATE THE TWO TABLES\n"
        "   Use the \"CodeAlerta\" (alert code) column to join the two "
        "—\n"
        "   it's the same key in both tables.\n\n"
        "NOTE ABOUT OVERLAPS\n"
        "   For Protected Area, Indigenous Land, Settlement, Quilombo,\n"
        "   Biosphere Reserve, Geopark, PPA, and Legal Reserve, the "
        "platform\n"
        "   itself calculates the area of each declaration\n"
        "   individually, WITHOUT removing overlaps between different\n"
        "   declarations. That means if two crossed territories "
        "overlap\n"
        "   each other, the sum of the individual areas can exceed the "
        "alert's\n"
        "   total area — this is expected and doesn't indicate an "
        "error.\n"
        "   For Biome, State, and Municipality, however, which don't "
        "overlap\n"
        "   each other, the sum of the individual areas always matches "
        "the\n"
        "   alert's total area."
    ),
}


TRANSLATIONS = {
    "es": {
        # Header / country and platform selection
        # "País"/"Idioma" are intentionally not included here — that
        # label is always fixed in English ("Country"/"Language"), see
        # the comment in main_dialog.py where they're created.
        "Plataforma": "Plataforma",
        "NOTA INFORMATIVA": "NOTA INFORMATIVA",
        "Acesso à API": "Acceso a la API",
        "API desconectada": "API desconectada",
        "API conectada como {}": "API conectada como {}",
        "API indisponível para {}": "API no disponible para {}",
        # Login
        "E-mail": "Correo electrónico",
        "E-mail da conta MapBiomas Alerta": (
            "Correo de la cuenta MapBiomas Alerta"
        ),
        "Senha": "Contraseña",
        "Salvar acesso": "Guardar acceso",
        "ENTRAR": "INGRESAR",
        "SAIR": "SALIR",
        "Mostrar": "Mostrar",
        "Ocultar": "Ocultar",
        "Mostrar/ocultar senha": "Mostrar/ocultar contraseña",
        # Main tabs
        "Nota informativa": "Nota informativa",
        "Filtros": "Filtros",
        "Camadas": "Capas",
        "Estatísticas": "Estadísticas",
        "Gráficos": "Gráficos",
        "Detalhes": "Detalles",
        # Filters tab — sections
        "1. Área de Interesse": "1. ÁREA DE INTERÉS",
        "2. Período": "2. PERÍODO",
        "3. Filtros": "3. FILTROS",
        "4. Cruzamentos": "4. CRUCES",
        # Area of interest
        "Todo o país selecionado": "Todo el país seleccionado",
        "Extensão de uma camada vetorial": "Extensión de una capa vectorial",
        "Informar coordenadas (um ponto)": "Indicar coordenadas (un punto)",
        "Buscar por código do alerta": "Buscar por código de alerta",
        "Buscar por imóvel rural (CAR)": (
            "Buscar por predio rural (catastro)"
        ),
        "Código do alerta": "Código de alerta",
        "Código do CAR": "Código de catastro",
        "Código numérico do alerta": "Código numérico de la alerta",
        "Código completo do CAR/SICAR": "Código completo del catastro",
        "Formato do código CAR válido.": "Formato de código válido.",
        # Period
        "Filtrar por": "Filtrar por",
        "Data de detecção": "Fecha de detección",
        "Data de publicação": "Fecha de publicación",
        "Data inicial": "Fecha inicial",
        "Data final": "Fecha final",
        # Filters
        "Área mínima": "Área mínima",
        "Fontes": "Fuentes",
        "Todas as fontes": "Todas las fuentes",
        "Selecionadas": "Seleccionadas",
        "Regra das fontes": "Regla de las fuentes",
        "Qualquer fonte selecionada": "Cualquier fuente seleccionada",
        "Todas selecionadas juntas": "Todas seleccionadas juntas",
        "Combinação exata": "Combinación exacta",
        # Crossings
        "Tipo": "Tipo",
        "Condição": "Condición",
        "Qualquer cruzamento disponível": "Cualquier cruce disponible",
        "Conecte-se à API para consultar as opções": (
            "Conéctese a la API para consultar las opciones"
        ),
        "Todos os alertas": "Todas las alertas",
        "Somente alertas com cruzamento": "Solo alertas con cruce",
        "Somente alertas sem cruzamento": "Solo alertas sin cruce",
        "Não foi possível consultar os cruzamentos": (
            "No fue posible consultar los cruces"
        ),
        "Nenhum cruzamento disponível nesta API": (
            "Ningún cruce disponible en esta API"
        ),
        "Unidades de Conservação (todas)": "Áreas Protegidas (todas)",
        "Terras Indígenas": "Territorios Indígenas",
        "Assentamentos": "Asentamientos",
        "Imóveis rurais": "Predios rurales",
        # Statistics tab
        "Resumo da consulta": "Resumen de la consulta",
        "Faça uma consulta para visualizar os resultados.": (
            "Realice una consulta para visualizar los resultados."
        ),
        "Comparação das camadas de consulta": (
            "Comparación de las capas de consulta"
        ),
        "Alertas encontrados": "Alertas encontradas",
        "Área total": "Área total",
        "Maior alerta": "Alerta más grande",
        "Código do maior alerta": "Código de la alerta más grande",
        "Local do maior alerta": "Ubicación de la alerta más grande",
        "Município com maior área": "Municipio con mayor área",
        "Menor alerta": "Alerta más pequeña",
        "Código do menor alerta": "Código de la alerta más pequeña",
        "Local do menor alerta": "Ubicación de la alerta más pequeña",
        "Velocidade de desmatamento": "Velocidad de deforestación",
        "Sobreposições com áreas protegidas e institucionais": (
            "Superposiciones con áreas protegidas e institucionales"
        ),
        "Tipo de data": "Tipo de fecha",
        "Período analisado": "Período analizado",
        "EXPORTAR ESTATÍSTICAS (XLSX)": "EXPORTAR ESTADÍSTICAS (XLSX)",
        "Análises estatísticas": "Análisis estadísticos",
        "Camada": "Capa",
        "Alertas": "Alertas",
        "Código": "Código",
        "Período": "Período",
        "Camada 1": "Capa 1",
        "Camada 2 (opcional)": "Capa 2 (opcional)",
        "Não comparar": "No comparar",
        "Barras": "Barras",
        "Pizza": "Circular",
        "Linha": "Línea",
        "Número de registros": "Número de registros",
        "Soma": "Suma",
        "Média": "Promedio",
        "Separar cada fonte": "Separar cada fuente",
        "Agrupar pela combinação": "Agrupar por combinación",
        "Todos os valores": "Todos los valores",
        "Tipo de gráfico": "Tipo de gráfico",
        "Campo para comparar": "Campo para comparar",
        "Cálculo": "Cálculo",
        "Campo numérico": "Campo numérico",
        "Fontes múltiplas": "Fuentes múltiples",
        "Valor específico": "Valor específico",
        "Categorias exibidas": "Categorías mostradas",
        "<b>Status:</b> Aguardando configuração.": (
            "<b>Estado:</b> Esperando configuración."
        ),
        "APLICAR ANÁLISE": "APLICAR ANÁLISIS",
        # Charts tab
        "Gráficos": "Gráficos",
        "Os dez maiores grupos são exibidos.": (
            "Se muestran los diez grupos más grandes."
        ),
        "EXPORTAR GRÁFICO PNG": "EXPORTAR GRÁFICO PNG",
        "EXPORTAR DADOS CSV": "EXPORTAR DATOS CSV",
        "EXPORTAR GPKG": "EXPORTAR GPKG",
        "EXPORTAR SHP": "EXPORTAR SHP",
        # Details tab
        "Detalhes do alerta": "Detalles de la alerta",
        "Identifique um alerta no mapa para consultar imagens e detalhes.": (
            "Identifique una alerta en el mapa para consultar "
            "imágenes y detalles."
        ),
        "IDENTIFICAR ALERTA NO MAPA": "IDENTIFICAR ALERTA EN EL MAPA",
        "Cruzamentos territoriais e ambientais": (
            "Cruces territoriales y ambientales"
        ),
        "Selecione um alerta para consultar os cruzamentos.": (
            "Seleccione una alerta para consultar los cruces."
        ),
        "Para saber mais sobre cruzamentos existentes, abra o laudo do "
        "alerta na plataforma.": (
            "Para saber más sobre los cruces existentes, abra el informe "
            "de la alerta en la plataforma."
        ),
        "Nenhum imóvel rural informado para este alerta.": (
            "Ningún predio rural informado para esta alerta."
        ),
        "OUTROS ALERTAS NOS MESMOS IMÓVEIS: {}": (
            "OTRAS ALERTAS EN LOS MISMOS PREDIOS: {}"
        ),
        "FECHAR ALERTAS RELACIONADOS": "CERRAR ALERTAS RELACIONADAS",
        "Imagem antes": "Imagen antes",
        "Imagem depois": "Imagen después",
        "Sem imagem": "Sin imagen",
        "ABRIR LAUDO NA PLATAFORMA": "ABRIR INFORME EN LA PLATAFORMA",
        "ANTERIOR": "ANTERIOR",
        "PRÓXIMO": "SIGUIENTE",
        "Imóveis cruzados pelo alerta": "Predios cruzados por la alerta",
        "Outros alertas nos mesmos imóveis": (
            "Otras alertas en los mismos predios"
        ),
        # Validation and error messages
        "O serviço ainda não está configurado.": (
            "El servicio aún no está configurado."
        ),
        "Leia e aceite a nota informativa antes de buscar alertas.": (
            "Lea y acepte la nota informativa antes de buscar alertas."
        ),
        "Entre na API MapBiomas Alerta antes de realizar a consulta.": (
            "Ingrese a la API de MapBiomas Alerta antes de realizar "
            "la consulta."
        ),
        "A data inicial não pode ser posterior à data final.": (
            "La fecha inicial no puede ser posterior a la fecha final."
        ),
        "Informe o código do alerta.": "Indique el código de la alerta.",
        "Informe o código do imóvel rural.": (
            "Indique el código del predio rural."
        ),
        "O código do CAR está fora do padrão esperado. Corrija o valor "
        "indicado antes de realizar a busca.": (
            "El código de catastro no tiene el formato esperado. "
            "Corrija el valor indicado antes de realizar la búsqueda."
        ),
        "O código do alerta deve conter somente números.": (
            "El código de la alerta debe contener solo números."
        ),
        "Código CAR reconhecido pela API.": (
            "Código de catastro reconocido por la API."
        ),
        "Não existe imóvel com o código informado ou ele não possui "
        "alertas.": (
            "No existe un predio con el código indicado, o no tiene "
            "alertas."
        ),
        "Não existe alerta com o código informado.": (
            "No existe una alerta con el código indicado."
        ),
        "O imóvel informado não possui alertas.": (
            "El predio indicado no tiene alertas."
        ),
        "Não existe alerta na coordenada indicada.": (
            "No existe una alerta en la coordenada indicada."
        ),
        "Não há gráfico para exportar.": "No hay gráfico para exportar.",
        "Não foi possível salvar o arquivo PNG.": (
            "No fue posible guardar el archivo PNG."
        ),
        "Não há tabela de estatísticas para exportar.": (
            "No hay tabla de estadísticas para exportar."
        ),
        "Não há dados filtrados para exportar.": (
            "No hay datos filtrados para exportar."
        ),
        "A camada não possui campos para exportar.": (
            "La capa no tiene campos para exportar."
        ),
        "Não há camada de alertas disponível.": (
            "No hay capa de alertas disponible."
        ),
        "O alerta selecionado não possui código.": (
            "La alerta seleccionada no tiene código."
        ),
        "A camada não possui alertas.": "La capa no tiene alertas.",
        "Sem cruzamento": "Sin cruce",
        "Ex.: -47.9292": "Ej.: -47.9292",
        "Ex.: -15.7801": "Ej.: -15.7801",
        "Disponível apenas quando a consulta é equivalente à da "
        "plataforma (sem recorte manual do mapa, todas as fontes e "
        "sem filtro de cruzamento).": (
            "Disponible solo cuando la búsqueda es equivalente a la de "
            "la plataforma (sin recorte manual del mapa, todas las "
            "fuentes y sin filtro de cruce)."
        ),
        "Não há nota informativa configurada para este país.": (
            "No hay una nota informativa configurada para este país."
        ),
        "ACESSAR A NOTA INFORMATIVA COMPLETA NA PLATAFORMA": (
            "ACCEDER A LA NOTA INFORMATIVA COMPLETA EN LA PLATAFORMA"
        ),
        "{} com maior área": "{} con mayor área",
        "Indisponível: a API não detalhou a área por {}": (
            "No disponible: la API no detalló el área por {}"
        ),
        "Este país não possui cadastro de imóveis rurais integrado à "
        "plataforma.": (
            "Este país no tiene un catastro de predios rurales "
            "integrado a la plataforma."
        ),
        "Nenhum cruzamento territorial ou ambiental (Unidade de "
        "Conservação, Terra Indígena, Assentamento etc.) foi "
        "registrado para este alerta. Imóveis rurais cruzados "
        "aparecem em uma seção própria, logo abaixo.": (
            "No se registró ningún cruce territorial o ambiental "
            "(Área Protegida, Territorio Indígena, Asentamiento etc.) "
            "para esta alerta. Los predios rurales cruzados aparecen "
            "en una sección propia, justo abajo."
        ),
        "A API deste país não disponibilizou campos de cruzamento "
        "compatíveis.": (
            "La API de este país no ofreció campos de cruce compatibles."
        ),
        "Alerta selecionado": "Alerta seleccionada",
        "Arquivo CSV (*.csv)": "Archivo CSV (*.csv)",
        "informações principais": "información principal",
        "tabela de atributos completa": "tabla de atributos completa",
        "Login realizado com sucesso.": "Inicio de sesión exitoso.",
        "{} alerta(s) carregado(s).": "{} alerta(s) cargada(s).",
        "Exportado em {}": "Exportado el {}",
        "Gráfico exportado para:\n{}": "Gráfico exportado a:\n{}",
        "Não foi possível exportar a tabela:\n{}": (
            "No fue posible exportar la tabla:\n{}"
        ),
        "Tabela exportada para:\n{}": "Tabla exportada a:\n{}",
        "Não foi possível exportar o CSV:\n{}": (
            "No fue posible exportar el CSV:\n{}"
        ),
        "{} registro(s) — {} — exportado(s) para:\n{}": (
            "{} registro(s) — {} — exportado(s) a:\n{}"
        ),
        "Configuração alterada. Clique em APLICAR ANÁLISE.": (
            "Configuración modificada. Haga clic en APLICAR ANÁLISIS."
        ),
        "<b>Status:</b> Configuração alterada. Clique em "
        "<b>APLICAR ANÁLISE</b>.": (
            "<b>Estado:</b> Configuración modificada. Haga clic en "
            "<b>APLICAR ANÁLISIS</b>."
        ),
        "<b>Status:</b> Selecione uma camada com pelo menos dois "
        "alertas ou escolha uma segunda camada para comparar.": (
            "<b>Estado:</b> Seleccione una capa con al menos dos "
            "alertas, o elija una segunda capa para comparar."
        ),
        "<b>Status:</b> A análise exige pelo menos dois alertas ou "
        "duas camadas para comparação.": (
            "<b>Estado:</b> El análisis requiere al menos dos alertas o "
            "dos capas para comparar."
        ),
        "Selecione uma camada com pelo menos dois alertas ou escolha "
        "uma segunda camada para comparar.": (
            "Seleccione una capa con al menos dos alertas, o elija una "
            "segunda capa para comparar."
        ),
        "PROCESSANDO ANÁLISE...": "PROCESANDO ANÁLISIS...",
        "<b>Status:</b> Processando os registros das camadas...": (
            "<b>Estado:</b> Procesando los registros de las capas..."
        ),
        "<b>Status:</b> Concluída sem campos analíticos comuns.": (
            "<b>Estado:</b> Concluido sin campos analíticos comunes."
        ),
        "As camadas não possuem campos analíticos comuns.": (
            "Las capas no tienen campos analíticos comunes."
        ),
        "<b>Status:</b> Análise concluída — {} camada(s), {} "
        "categoria(s), {:.1f} segundo(s).": (
            "<b>Estado:</b> Análisis concluido — {} capa(s), {} "
            "categoría(s), {:.1f} segundo(s)."
        ),
        "<b>Status:</b> Análise concluída, mas a configuração "
        "selecionada não produziu dados para o gráfico.": (
            "<b>Estado:</b> Análisis concluido, pero la configuración "
            "seleccionada no produjo datos para el gráfico."
        ),
        "<b>Status:</b> Falha ao executar a análise.": (
            "<b>Estado:</b> Error al ejecutar el análisis."
        ),
        "Não foi possível aplicar a análise: {}": (
            "No fue posible aplicar el análisis: {}"
        ),
        "Área": "Área",
        # Details tab — dynamic messages
        "A sessão expirou antes de carregar o alerta.": (
            "La sesión expiró antes de cargar la alerta."
        ),
        "Não foi possível carregar o alerta.": (
            "No fue posible cargar la alerta."
        ),
        "Alerta {} carregado.": "Alerta {} cargada.",
        "Detecção": "Detección",
        "Publicação": "Publicación",
        "Fonte(s)": "Fuente(s)",
        "Bioma(s)": "Bioma(s)",
        "Imóvel rural — {}": "Predio rural — {}",
        "{} imóvel(is) cruzado(s)": "{} predio(s) cruzado(s)",
        "VER {} OUTRO(S) ALERTA(S) E SUAS IMAGENS": (
            "VER {} OTRA(S) ALERTA(S) Y SUS IMÁGENES"
        ),
        "Consultando os imóveis relacionados ao alerta...": (
            "Consultando los predios relacionados con la alerta..."
        ),
        "CONSULTANDO OUTROS ALERTAS...": "CONSULTANDO OTRAS ALERTAS...",
        "REABRIR OUTROS ALERTAS E SUAS IMAGENS": (
            "REABRIR OTRAS ALERTAS Y SUS IMÁGENES"
        ),
        "OUTROS ALERTAS E IMAGENS ADICIONADOS ABAIXO": (
            "OTRAS ALERTAS E IMÁGENES AGREGADAS ABAJO"
        ),
        "Os alertas relacionados e suas imagens já estão carregados.": (
            "Las alertas relacionadas y sus imágenes ya están cargadas."
        ),
        "Não há uma camada de alertas disponível para esta consulta.": (
            "No hay una capa de alertas disponible para esta consulta."
        ),
        "Preparando a consulta dos alertas e das imagens...": (
            "Preparando la consulta de las alertas y las imágenes..."
        ),
        "PROCESSANDO OUTROS ALERTAS...": "PROCESANDO OTRAS ALERTAS...",
        "Nenhum outro alerta foi encontrado nos mesmos imóveis.": (
            "No se encontró ninguna otra alerta en los mismos predios."
        ),
        "Outros alertas encontrados": "Otras alertas encontradas",
        "Imóvel {} — {} outro(s) alerta(s)": (
            "Predio {} — {} otra(s) alerta(s)"
        ),
        "Tipo": "Tipo",
        "Área do imóvel": "Área del predio",
        "Carregando alerta {} de {} (código {}) e suas imagens...": (
            "Cargando alerta {} de {} (código {}) y sus imágenes..."
        ),
        "CARREGANDO ALERTA {}/{}...": "CARGANDO ALERTA {}/{}...",
        "Processamento concluído: {} outro(s) alerta(s) e suas "
        "imagens foram carregados.": (
            "Procesamiento concluido: {} otra(s) alerta(s) y sus "
            "imágenes fueron cargadas."
        ),
        "Unidades de Conservação": "Áreas Protegidas",
        "Área em Unidade de Conservação": "Área en Área Protegida",
        "Área em Terra Indígena": "Área en Territorio Indígena",
        "Área em assentamentos": "Área en asentamientos",
        "Territórios quilombolas": "Territorios quilombolas",
        "Área quilombola": "Área quilombola",
        "Reservas da Biosfera": "Reservas de la Biosfera",
        "Área em Reserva da Biosfera": "Área en Reserva de la Biosfera",
        "Manejo florestal": "Manejo forestal",
        "Área de manejo": "Área de manejo",
        "Proteção integral federal": "Protección integral federal",
        "Área de proteção integral": "Área de protección integral",
        "Uso sustentável federal": "Uso sostenible federal",
        "Área de uso sustentável": "Área de uso sostenible",
        "Área de Preservação Permanente": "Área de Preservación Permanente",
        "APPs": "APPs",
        "Área de Reserva Legal": "Área de Reserva Legal",
        "Reservas Legais": "Reservas Legales",
        "Territórios especiais": "Territorios especiales",
        "Área em território especial": "Área en territorio especial",
        "VER NO MAPA": "VER EN EL MAPA",
        "Não foi possível carregar as imagens.": (
            "No fue posible cargar las imágenes."
        ),
        "Centralizar este alerta no mapa.": "Centrar esta alerta en el mapa.",
        "A API não retornou a geometria deste alerta.": (
            "La API no devolvió la geometría de esta alerta."
        ),
        "Imagem não disponibilizada pela API.": (
            "Imagen no disponible en la API."
        ),
        "Formato de imagem não reconhecido.": (
            "Formato de imagen no reconocido."
        ),
        "O servidor de imagens não respondeu. Tente novamente mais "
        "tarde.": (
            "El servidor de imágenes no respondió. Intente de nuevo "
            "más tarde."
        ),
        # API error messages (api_client.py)
        "Informe o e-mail e a senha.": "Indique el correo y la contraseña.",
        "A API não retornou um token de acesso.": (
            "La API no devolvió un token de acceso."
        ),
        "Faça login na API antes de buscar alertas.": (
            "Inicie sesión en la API antes de buscar alertas."
        ),
        "A API não informou metadata.totalCount; não é possível "
        "garantir que todos os alertas foram recebidos.": (
            "La API no informó metadata.totalCount; no es posible "
            "garantizar que se recibieron todas las alertas."
        ),
        "A paginação informada pela API é inconsistente.": (
            "La paginación informada por la API es inconsistente."
        ),
        "A API entregou mais alertas do que metadata.totalCount. A "
        "consulta foi interrompida para evitar dados incorretos.": (
            "La API entregó más alertas de las indicadas en "
            "metadata.totalCount. La consulta se interrumpió para "
            "evitar datos incorrectos."
        ),
        "A consulta estatística da plataforma não informou o total de "
        "alertas. Nenhuma camada foi criada sem essa validação.": (
            "La consulta estadística de la plataforma no informó el "
            "total de alertas. No se creó ninguna capa sin esta "
            "validación."
        ),
        "A consulta estatística retornou uma área inválida.": (
            "La consulta estadística devolvió un área inválida."
        ),
        "A API devolveu um código diferente do solicitado.": (
            "La API devolvió un código diferente al solicitado."
        ),
        "A API não encontrou o alerta informado.": (
            "La API no encontró la alerta indicada."
        ),
        "O servidor de imagens está temporariamente indisponível.": (
            "El servidor de imágenes está temporalmente no disponible."
        ),
        "O servidor de imagens não respondeu em 30 segundos.": (
            "El servidor de imágenes no respondió en 30 segundos."
        ),
        "A sessão da API não está autenticada.": (
            "La sesión de la API no está autenticada."
        ),
        "A consulta à API excedeu 120 segundos.": (
            "La consulta a la API superó los 120 segundos."
        ),
        "A API recusou o acesso (HTTP 403).": (
            "La API rechazó el acceso (HTTP 403)."
        ),
        "O limite de requisições da API foi atingido (HTTP 429). "
        "Aguarde e tente novamente.": (
            "Se alcanzó el límite de solicitudes de la API (HTTP 429). "
            "Espere e intente de nuevo."
        ),
        "A API retornou uma resposta inválida.": (
            "La API devolvió una respuesta inválida."
        ),
        "Exportar dados CSV": "Exportar datos CSV",
        "Qual conteúdo você deseja exportar?": (
            "¿Qué contenido desea exportar?"
        ),
        "Será criado somente um arquivo CSV com a opção escolhida.": (
            "Se creará solo un archivo CSV con la opción elegida."
        ),
        "INFORMAÇÕES PRINCIPAIS": "INFORMACIÓN PRINCIPAL",
        "TABELA DE ATRIBUTOS COMPLETA": "TABLA DE ATRIBUTOS COMPLETA",
        "Área (ha)": "Área (ha)",
        "API desconectada": "API desconectada",
        "API indisponível para {}": "API no disponible para {}",
        "NOTA ACEITA": "NOTA ACEPTADA",
        "Conectando à API...": "Conectando a la API...",
        "A sessão da API expirou. Entre novamente.": (
            "La sesión de la API expiró. Vuelva a iniciar sesión."
        ),
        "O login foi realizado, mas o QGIS não conseguiu salvar as "
        "credenciais no Gerenciador de Autenticação.": (
            "Se inició sesión, pero QGIS no pudo guardar las "
            "credenciales en el Gestor de Autenticación."
        ),
        "API conectada como {}": "API conectada como {}",
        "Falha no login automático": "Error en el inicio de sesión automático",
        "Falha na autenticação": "Error de autenticación",
        "Sessão expirada": "Sesión expirada",
        "SERVIÇO AINDA NÃO CONFIGURADO": "SERVICIO AÚN NO CONFIGURADO",
        "FAÇA LOGIN PARA BUSCAR": "INICIE SESIÓN PARA BUSCAR",
        "COORDENADAS — UM PONTO": "COORDENADAS — UN PUNTO",
        "Longitude": "Longitud",
        "Latitude": "Latitud",
        "Sistema de referência: WGS 84 (EPSG:4326)": (
            "Sistema de referencia: WGS 84 (EPSG:4326)"
        ),
        "A consulta abrangerá todo o {}. Use período, área mínima e "
        "fontes para limitar o volume.": (
            "La consulta abarcará todo el {}. Use el período, el área "
            "mínima y las fuentes para limitar el volumen."
        ),
        "A validação do formato depende do cadastro do país "
        "selecionado.": (
            "La validación del formato depende del catastro del país "
            "seleccionado."
        ),
        "Formato inválido. Use UF-0000000-"
        "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.": (
            "Formato inválido. Use UF-0000000-"
            "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX."
        ),
        "Campo de área não encontrado": "Campo de área no encontrado",
        "Não aplicado": "No aplicado",
        "Data de publicação": "Fecha de publicación",
        "Data de detecção": "Fecha de detección",
        "{} até {}": "{} hasta {}",
        "Média da consulta: {} ha/dia": "Promedio de la consulta: {} ha/día",
        "Maior velocidade: {} ha/dia": "Mayor velocidad: {} ha/día",
        "alerta {}": "alerta {}",
        "Unidades de Conservação": "Áreas Protegidas",
        "Terras Indígenas": "Territorios Indígenas",
        "Assentamentos": "Asentamientos",
        "Reservas Legais": "Reservas Legales",
        "Áreas de Preservação Permanente": "Áreas de Preservación Permanente",
        "Manejo Florestal": "Manejo Forestal",
        "Nascentes de Rios": "Nacientes de Ríos",
        "Imóveis Rurais (CAR)": "Predios Rurales (catastro)",
        "Áreas Autorizadas": "Áreas Autorizadas",
        "Ações de Fiscalização": "Acciones de Fiscalización",
        "Escolha as opções e clique em APLICAR ANÁLISE.": (
            "Elija las opciones y haga clic en APLICAR ANÁLISIS."
        ),
        "Consulta concluída com sucesso.": (
            "Consulta concluida con éxito."
        ),
        "A consulta foi concluída, mas nenhum alerta foi encontrado.": (
            "La consulta se concluyó, pero no se encontró ninguna alerta."
        ),
        "A identificação está ativa. Clique em outro alerta no mapa.": (
            "La identificación está activa. Haga clic en otra alerta "
            "en el mapa."
        ),
        "Clique em um alerta de qualquer camada criada pelo plugin.": (
            "Haga clic en una alerta de cualquier capa creada por el "
            "plugin."
        ),
        "A camada não possui o código necessário para consultar o "
        "alerta.": (
            "La capa no tiene el código necesario para consultar la "
            "alerta."
        ),
        "Carregando detalhes do alerta {}...": (
            "Cargando detalles de la alerta {}..."
        ),
        "Todo o {}": "Todo el {}",
        "Camada vetorial": "Capa vectorial",
        "Código do alerta{}": "Código de alerta{}",
        "Imóvel rural{}": "Predio rural{}",
        "Coordenadas": "Coordenadas",
        "{} · {} · sem filtros adicionais": "{} · {} · sin filtros adicionales",
        "{} fonte(s) — {}": "{} fuente(s) — {}",
        "mín. {} ha": "mín. {} ha",
        "{} · {} · {} a {} · {}": "{} · {} · {} a {} · {}",
        "sem período adicional": "sin período adicional",
        "{}. {} | {} | {} alerta(s)": "{}. {} | {} | {} alerta(s)",
        "{} camada(s) filtrada(s).": "{} capa(s) filtrada(s).",
        "Selecione um campo da tabela para realizar a comparação.": (
            "Seleccione un campo de la tabla para realizar la comparación."
        ),
        "A camada não possui campos numéricos para este cálculo.": (
            "La capa no tiene campos numéricos para este cálculo."
        ),
        # Help texts ("ⓘ" icons)
        "Consulta um alerta específico pelo código da plataforma. "
        "Quando preenchido, o código substitui o recorte espacial.": (
            "Consulta una alerta específica por el código de la "
            "plataforma. Cuando se completa, el código reemplaza el "
            "recorte espacial."
        ),
        "Busca todos os alertas vinculados ao imóvel rural, usando o "
        "código de cadastro (CAR/SICAR) no padrão "
        "UF-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (ex.: "
        "PE-2610905-7821EE203D0441D699AA58725AC25249). Segundo a "
        "documentação oficial da API, essa busca só retorna "
        "resultado para imóveis que já têm pelo menos um alerta — "
        "um código válido mas sem nenhum alerta não gera erro, só "
        "não aparece nada.": (
            "Busca todas las alertas vinculadas al predio rural, "
            "usando el código de catastro (CAR/SICAR) en el patrón "
            "UF-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (ej.: "
            "PE-2610905-7821EE203D0441D699AA58725AC25249). Según la "
            "documentación oficial de la API, esta búsqueda solo "
            "devuelve resultado para predios que ya tienen al menos "
            "una alerta — un código válido pero sin ninguna alerta "
            "no genera error, simplemente no aparece nada."
        ),
        "Define se o período se aplica à detecção ou à publicação.": (
            "Define si el período se aplica a la detección o a la "
            "publicación."
        ),
        "Primeiro dia incluído na consulta.": (
            "Primer día incluido en la consulta."
        ),
        "Último dia incluído na consulta.": (
            "Último día incluido en la consulta."
        ),
        "Exclui alertas menores que a área informada, em hectares.": (
            "Excluye alertas menores que el área indicada, en hectáreas."
        ),
        "Selecione uma ou mais fontes de detecção disponibilizadas "
        "pela API.": (
            "Seleccione una o más fuentes de detección disponibles en "
            "la API."
        ),
        "Define se basta qualquer fonte, se todas devem estar "
        "presentes ou se a combinação deve ser exata.": (
            "Define si basta con cualquier fuente, si todas deben "
            "estar presentes, o si la combinación debe ser exacta."
        ),
        "Base territorial ou ambiental usada para verificar "
        "cruzamentos.": (
            "Base territorial o ambiental usada para verificar cruces."
        ),
        "Inclui todos os alertas ou somente os que têm ou não têm "
        "cruzamento.": (
            "Incluye todas las alertas o solo las que tienen o no "
            "tienen cruce."
        ),
        "Define a forma de exibição do resultado na aba Gráficos.": (
            "Define la forma de mostrar el resultado en la pestaña "
            "Gráficos."
        ),
        "Agrupa os alertas pelo atributo escolhido. A opção 'Áreas "
        "por tipo de cruzamento' compara a soma, em hectares, de cada "
        "sobreposição territorial informada pela API; como os tipos "
        "podem se sobrepor, as barras não representam parcelas "
        "exclusivas da área total.": (
            "Agrupa las alertas por el atributo elegido. La opción "
            "'Áreas por tipo de cruce' compara la suma, en hectáreas, "
            "de cada superposición territorial informada por la API; "
            "como los tipos pueden superponerse, las barras no "
            "representan partes exclusivas del área total."
        ),
        "Escolhe entre contagem, soma ou média do campo numérico.": (
            "Elige entre conteo, suma o promedio del campo numérico."
        ),
        "Atributo usado nos cálculos de soma e média.": (
            "Atributo usado en los cálculos de suma y promedio."
        ),
        "Separa cada fonte ou mantém a combinação registrada no "
        "alerta.": (
            "Separa cada fuente o mantiene la combinación registrada "
            "en la alerta."
        ),
        "Restringe o gráfico a uma categoria do campo de comparação.": (
            "Restringe el gráfico a una categoría del campo de "
            "comparación."
        ),
        "Limita quantos grupos do ranking aparecem no gráfico.": (
            "Limita cuántos grupos del ranking aparecen en el gráfico."
        ),
        "Informe e-mail e senha para acessar a API.": (
            "Indique el correo y la contraseña para acceder a la API."
        ),
        "Consulta concluída. {} de {} alerta(s) atendem à condição de "
        "cruzamento.": (
            "Consulta concluida. {} de {} alerta(s) cumplen la "
            "condición de cruce."
        ),
        "{} alerta(s) foram ignorados por não possuírem geometria "
        "válida.": (
            "{} alerta(s) fueron ignoradas por no tener geometría "
            "válida."
        ),
        "Consulta carregada com ressalvas. ": (
            "Consulta cargada con salvedades. "
        ),
        "Consulta por CAR: somente tempo, fontes e métricas de área "
        "com dados válidos podem ser analisados.": (
            "Consulta por catastro: solo tiempo, fuentes y métricas "
            "de área con datos válidos pueden analizarse."
        ),
        "Consulta por coordenada: somente tempo, fontes e métricas de "
        "área com dados válidos podem ser analisados.": (
            "Consulta por coordenada: solo tiempo, fuentes y métricas "
            "de área con datos válidos pueden analizarse."
        ),
        "Esta combinação não pode ser calculada com precisão com os "
        "campos fornecidos pela API. Use Número de registros.": (
            "Esta combinación no puede calcularse con precisión con "
            "los campos proporcionados por la API. Use Número de "
            "registros."
        ),
        "Faça uma consulta para visualizar as estatísticas.": (
            "Realice una consulta para visualizar las estadísticas."
        ),
        "Consultar novamente a nota informativa do país selecionado.": (
            "Consultar de nuevo la nota informativa del país "
            "seleccionado."
        ),
        "Identifique um alerta no mapa para consultar imagens e "
        "detalhes.": (
            "Identifique una alerta en el mapa para consultar "
            "imágenes y detalles."
        ),
        " de {}": " de {}",
        "Cada barra soma a área numérica informada pela API para o "
        "respectivo tipo de cruzamento. Os tipos podem se sobrepor; "
        "não some as barras como se fossem área exclusiva.": (
            "Cada barra suma el área numérica informada por la API "
            "para el respectivo tipo de cruce. Los tipos pueden "
            "superponerse; no sume las barras como si fueran área "
            "exclusiva."
        ),
        "Resultado agregado pela API para os mesmos filtros da "
        "camada.": (
            "Resultado agregado por la API para los mismos filtros "
            "de la capa."
        ),
        "Áreas individualizadas por território apenas quando há "
        "alocação exata na API ou interseção geométrica com cada "
        "feição da camada selecionada.": (
            "Áreas individualizadas por territorio solo cuando hay "
            "asignación exacta en la API o intersección geométrica "
            "con cada entidad de la capa seleccionada."
        ),
        "Alertas com múltiplas fontes aparecem uma vez em cada "
        "fonte; a soma das categorias pode superar o total da "
        "consulta.": (
            "Las alertas con múltiples fuentes aparecen una vez en "
            "cada fuente; la suma de las categorías puede superar el "
            "total de la consulta."
        ),
        "Um alerta pode aparecer em mais de uma categoria "
        "territorial.": (
            "Una alerta puede aparecer en más de una categoría "
            "territorial."
        ),
        "{}: {}{} por {}{}. Exibindo {} grupo(s). {}": (
            "{}: {}{} por {}{}. Mostrando {} grupo(s). {}"
        ),
        "Comparação entre duas camadas": "Comparación entre dos capas",
        "Ranking": "Ranking",
        "tipo de cruzamento": "tipo de cruce",
        " — filtro: {}": " — filtro: {}",
        "ABRIR PASTA": "ABRIR CARPETA",
        "Não foi possível verificar os cruzamentos disponíveis para {} "
        "— tente novamente mais tarde.": (
            "No fue posible verificar los cruces disponibles para {} "
            "— intente de nuevo más tarde."
        ),
        "LI E CONCORDO": "LEÍ Y ACEPTO",
        "Consulta e análise de alertas de desmatamento no QGIS": (
            "Consulta y análisis de alertas de deforestación en QGIS"
        ),
        "ENTRAR NA API": "INGRESAR A LA API",
        "Salvar acesso no QGIS": "Guardar acceso en QGIS",
        "Manter acesso salvo neste perfil do QGIS": (
            "Mantener el acceso guardado en este perfil de QGIS"
        ),
        "As credenciais serão protegidas pelo Gerenciador de "
        "Autenticação do QGIS.": (
            "Las credenciales estarán protegidas por el Gestor de "
            "Autenticación de QGIS."
        ),
        "Selecione uma camada vetorial.": "Seleccione una capa vectorial.",
        "{} feição(ões) na camada.": "{} entidad(es) en la capa.",
        "{} a {}": "{} a {}",
        "Bioma": "Bioma",
        "Fonte": "Fuente",
        "Área do alerta": "Área de la alerta",
        "Define o recorte espacial da busca: todo o país selecionado, "
        "uma camada vetorial já carregada, um ponto por coordenadas, "
        "um alerta específico pelo código, ou um imóvel rural pelo "
        "código do cadastro.": (
            "Define el recorte espacial de la búsqueda: todo el país "
            "seleccionado, una capa vectorial ya cargada, un punto "
            "por coordenadas, una alerta específica por su código, o "
            "un predio rural por el código de catastro."
        ),
        "Para acessar a API é necessário ter um login cadastrado na "
        "plataforma MapBiomas Alerta do país selecionado. Se ainda "
        "não tiver uma conta, cadastre-se no site oficial antes de "
        "entrar aqui.": (
            "Para acceder a la API es necesario tener un inicio de "
            "sesión registrado en la plataforma MapBiomas Alerta del "
            "país seleccionado. Si aún no tiene una cuenta, "
            "regístrese en el sitio oficial antes de ingresar aquí."
        ),
        "Acesse: {}": "Acceda a: {}",
        "Incluir dados de cruzamento territorial na camada": (
            "Incluir datos de cruce territorial en la capa"
        ),
        "O período selecionado tem mais de 1 ano. Reduza o intervalo "
        "de datas — se precisar de um período maior, faça mais de "
        "uma busca (uma para cada ano, por exemplo).": (
            "El período seleccionado tiene más de 1 año. Reduzca el "
            "intervalo de fechas — si necesita un período más largo, "
            "haga más de una búsqueda (una por año, por ejemplo)."
        ),
        "Esta busca deve retornar aproximadamente {} alertas e pode "
        "demorar um pouco. Períodos mais curtos deixam a busca mais "
        "rápida.": (
            "Esta búsqueda debería devolver aproximadamente {} "
            "alertas y puede tardar un poco. Los períodos más cortos "
            "hacen la búsqueda más rápida."
        ),
        "Desmarque para buscas mais rápidas quando você não precisa "
        "dos detalhes de cruzamento (Unidade de Conservação, Terra "
        "Indígena, Assentamento etc.) — o filtro de Cruzamentos "
        "continua funcionando normalmente mesmo desmarcado. Com a "
        "opção desmarcada, a aba Detalhes de cada alerta continua "
        "mostrando os cruzamentos normalmente (ela já consulta isso "
        "à parte, por alerta), mas a exportação 'Tabela de atributos "
        "completa', 'Cruzamentos territoriais' e o gráfico 'Áreas "
        "por tipo de cruzamento' ficam indisponíveis para essa "
        "camada — refaça a busca com a opção marcada se precisar "
        "deles depois.": (
            "Desmarque para búsquedas más rápidas cuando no necesite "
            "los detalles de cruce (Área Protegida, Territorio "
            "Indígena, Asentamiento etc.) — el filtro de Cruces sigue "
            "funcionando normalmente aunque esté desmarcado. Con la "
            "opción desmarcada, la pestaña Detalles de cada alerta "
            "sigue mostrando los cruces normalmente (ya consulta eso "
            "aparte, por alerta), pero la exportación 'Tabla de "
            "atributos completa', 'Cruces territoriales' y el "
            "gráfico 'Áreas por tipo de cruce' quedan no disponibles "
            "para esa capa — repita la búsqueda con la opción "
            "marcada si los necesita después."
        ),
        "Não foi possível exportar a camada:\n{}": (
            "No fue posible exportar la capa:\n{}"
        ),
        "A camada espacial foi exportada, mas a tabela de cruzamentos "
        "falhou:\n{}": (
            "La capa espacial fue exportada, pero la tabla de cruces "
            "falló:\n{}"
        ),
        "A camada espacial foi exportada, mas o CSV de cruzamentos "
        "falhou:\n{}": (
            "La capa espacial fue exportada, pero el CSV de cruces "
            "falló:\n{}"
        ),
        "Camada exportada para:\n{}": "Capa exportada a:\n{}",
        "\n\nCruzamentos: tabela interna 'cruzamentos' no GeoPackage.": (
            "\n\nCruces: tabla interna 'cruzamentos' en el GeoPackage."
        ),
        "\n\nCruzamentos (formato longo, um por linha): {}": (
            "\n\nCruces (formato largo, uno por línea): {}"
        ),
        "\n\nVeja {} para entender a diferença entre as tabelas (a de "
        "cruzamentos tem muito mais linhas — isso é esperado).": (
            "\n\nVea {} para entender la diferencia entre las tablas "
            "(la de cruces tiene muchas más líneas — esto es esperado)."
        ),
        "\n\nObservação: o Shapefile limita nomes de campos. Use "
        "GeoPackage quando precisar preservar melhor a estrutura.": (
            "\n\nNota: el Shapefile limita los nombres de los campos. "
            "Use GeoPackage cuando necesite preservar mejor la "
            "estructura."
        ),
        # Layers tab
        "Camada de alertas": "Capa de alertas",
        "Nenhuma consulta realizada.": "Ninguna consulta realizada.",
        "Escolha qual camada de consulta alimenta o gráfico.": (
            "Elija qué capa de consulta alimenta el gráfico."
        ),
        "Nenhuma camada filtrada.": "Ninguna capa filtrada.",
        "Abrir tabela de atributos": "Abrir tabla de atributos",
        "Remover camada": "Eliminar capa",
        "Exportar camada em CSV": "Exportar capa en CSV",
        "Conteúdo do arquivo": "Contenido del archivo",
        "Informações principais": "Información principal",
        "Tabela de atributos completa": "Tabla de atributos completa",
        "EXPORTAR CSV": "EXPORTAR CSV",
        (
            "Existem 3 formatos porque cada um responde uma pergunta "
            "diferente:\n\n"
            "• Informações principais — 1 linha por alerta, só os "
            "campos essenciais (código, área, data, bioma/estado/"
            "município). O jeito mais simples de olhar a lista de "
            "alertas.\n\n"
            "• Tabela de atributos completa — 1 linha por alerta, com "
            "TODOS os campos da camada. A divisão de área por "
            "território (UC, TI, assentamento etc.) vem dentro de "
            "colunas com texto em JSON, então cada alerta ainda ocupa "
            "só 1 linha, mesmo cruzando vários territórios.\n\n"
            "• Cruzamentos territoriais — formato longo: 1 linha para "
            "CADA território que cada alerta cruza. Um único alerta que "
            "cruza 3 territórios diferentes gera 3 linhas aqui. Por "
            "isso esta tabela sempre tem MUITO mais linhas que as "
            "outras duas — não é duplicação nem erro, é o mesmo dado "
            "reorganizado para ser fácil de somar, filtrar ou cruzar "
            "com outras planilhas, já sem o JSON."
        ): (
            "Existen 3 formatos porque cada uno responde una pregunta "
            "diferente:\n\n"
            "• Información principal — 1 línea por alerta, solo los "
            "campos esenciales (código, área, fecha, bioma/departamento/"
            "municipio). La forma más simple de ver la lista de "
            "alertas.\n\n"
            "• Tabla de atributos completa — 1 línea por alerta, con "
            "TODOS los campos de la capa. La división de área por "
            "territorio (UC, TI, asentamiento etc.) viene dentro de "
            "columnas con texto en JSON, así que cada alerta sigue "
            "ocupando solo 1 línea, aunque cruce varios territorios.\n\n"
            "• Cruces territoriales — formato largo: 1 línea para CADA "
            "territorio que cada alerta cruza. Una sola alerta que "
            "cruza 3 territorios diferentes genera 3 líneas aquí. Por "
            "eso esta tabla siempre tiene MUCHAS más líneas que las "
            "otras dos — no es duplicación ni error, es el mismo dato "
            "reorganizado para ser fácil de sumar, filtrar o cruzar "
            "con otras planillas, ya sin el JSON."
        ),
        # Main buttons
        "BUSCAR ALERTAS": "BUSCAR ALERTAS",
        "LIMPAR": "LIMPIAR",
        "CANCELAR": "CANCELAR",
        "BAIXANDO...": "DESCARGANDO...",
        "CONSULTANDO RESUMO...": "CONSULTANDO RESUMEN...",
        "BAIXANDO {}/{}...": "DESCARGANDO {}/{}...",
        "PROCESSANDO {}/{}...": "PROCESANDO {}/{}...",
        "FINALIZANDO...": "FINALIZANDO...",
        # Biome filter / chart window / layer category
        'Todos os biomas': 'Todos los biomas',
        'Limita a busca a um ou mais biomas, sem precisar carregar uma camada vetorial. A lista vem da própria API da plataforma.': 'Limita la búsqueda a uno o más biomas, sin necesidad de cargar una capa vectorial. La lista viene de la propia API de la plataforma.',
        'AMPLIAR GRÁFICO': 'AMPLIAR GRÁFICO',
        'Gráfico': 'Gráfico',
        'FECHAR': 'CERRAR',
        'Não há gráfico para exibir.': 'No hay gráfico para mostrar.',
        'A camada representa': 'La capa representa',
        'Detectar automaticamente': 'Detectar automáticamente',
        'Terra indígena': 'Tierra indígena',
        'Unidade de conservação': 'Unidad de conservación',
        'Território quilombola': 'Territorio quilombola',
        'Município': 'Municipio',
        'Estado / departamento': 'Estado / departamento',
        'Assentamento': 'Asentamiento',
        'Define o tipo de território da camada escolhida, usado para nomear a categoria nas tabelas de cruzamento e nas exportações. No modo automático, o plugin tenta reconhecer pelo nome da camada e depois pelos campos.': 'Define el tipo de territorio de la capa elegida, usado para nombrar la categoría en las tablas de cruce y en las exportaciones. En modo automático, el plugin intenta reconocerlo por el nombre de la capa y luego por los campos.',
        # Panel layout
        'Todo o país': 'Todo el país',
        'Coordenada (ponto)': 'Coordenada (punto)',
        'Imóvel rural (CAR)': 'Predio rural (CAR)',
        'Últimos 30 dias': 'Últimos 30 días',
        '90 dias': '90 días',
        'Este ano': 'Este año',
        '⤢ AMPLIAR': '⤢ AMPLIAR',
        'Abre o gráfico numa janela maior, com todas as categorias.': 'Abre el gráfico en una ventana más grande, con todas las categorías.',
        'área ≥ {} ha': 'área ≥ {} ha',
        'com dados de cruzamento': 'con datos de cruce',
        'sem dados de cruzamento': 'sin datos de cruce',
        # Panel layout (continued)
        'Um ou mais biomas, sem precisar carregar uma camada vetorial.': 'Uno o más biomas, sin cargar una capa vectorial.',
        'Selecione um ou mais biomas': 'Seleccione uno o más biomas',
        'Limita a busca aos biomas escolhidos. O recorte é feito pela própria API da plataforma, com contagem e área exatas.': 'Limita la búsqueda a los biomas elegidos. El recorte lo hace la propia API de la plataforma, con conteo y área exactos.',
        'Entre na API para carregar a lista de biomas.': 'Ingrese a la API para cargar la lista de biomas.',
        'A API deste país não informou a lista de biomas. Use uma camada vetorial do bioma como área de interesse.': 'La API de este país no informó la lista de biomas. Use una capa vectorial del bioma como área de interés.',
        'Selecione ao menos um bioma para a busca.': 'Seleccione al menos un bioma para la búsqueda.',
        'Camada vetorial já carregada no QGIS cuja geometria define o recorte da busca.': 'Capa vectorial ya cargada en QGIS cuya geometría define el recorte de la búsqueda.',
        'Selecione um alerta para ver os imóveis cruzados.': 'Seleccione una alerta para ver los predios cruzados.',
        'Visualização rápida no mapa': 'Vista rápida en el mapa',
        'Mostra os alertas no mapa direto do servidor da plataforma, com as estatísticas da API, sem baixar os polígonos. Os polígonos só são baixados, automaticamente, quando você exporta, gera um gráfico ou abre os detalhes de um alerta. Com filtro de fonte ou de cruzamento, a busca baixa os polígonos direto.': 'Muestra las alertas en el mapa directamente desde el servidor de la plataforma, con las estadísticas de la API, sin descargar los polígonos. Los polígonos solo se descargan, automáticamente, cuando exporta, genera un gráfico o abre los detalles de una alerta. Con filtro de fuente o de cruce, la búsqueda descarga los polígonos directamente.',
        'Visualização rápida indisponível ({}). Baixando os alertas pela API.': 'Vista rápida no disponible ({}). Descargando las alertas por la API.',
        '{} alerta(s), {} ha — mostrados no mapa sem baixar os polígonos. Eles serão baixados automaticamente se você exportar, gerar um gráfico ou abrir os detalhes de um alerta. Alertas pequenos podem não aparecer em escalas muito pequenas: aproxime o mapa.': '{} alerta(s), {} ha — mostradas en el mapa sin descargar los polígonos. Se descargarán automáticamente si exporta, genera un gráfico o abre los detalles de una alerta. Las alertas pequeñas pueden no aparecer en escalas muy pequeñas: acerque el mapa.',
        'Baixando os polígonos dos alertas para esta ação...': 'Descargando los polígonos de las alertas para esta acción...',
        '{} ha': '{} ha',
        'até': 'hasta',
        'a camada do servidor não permite filtrar por bioma': 'la capa del servidor no permite filtrar por bioma',
        'o servidor de mapas não respondeu': 'el servidor de mapas no respondió',
        'nenhuma camada de alertas publicada no servidor de mapas': 'ninguna capa de alertas publicada en el servidor de mapas',
        # Search progress and summary
        'Baixando os alertas...': 'Descargando las alertas...',
        'Os números abaixo já são os oficiais da plataforma para estes filtros. A camada aparece no mapa ao terminar.': 'Los números de abajo ya son los oficiales de la plataforma para estos filtros. La capa aparece en el mapa al terminar.',
        'Números da plataforma para o retângulo da camada; ao terminar, são recalculados com o recorte exato.': 'Números de la plataforma para el rectángulo de la capa; al terminar, se recalculan con el recorte exacto.',
        'Baixando os alertas… página {} de {}': 'Descargando las alertas… página {} de {}',
        'Total de alertas': 'Total de alertas',
        'Área desmatada (ha)': 'Área deforestada (ha)',
        'Média diária (ha/dia)': 'Promedio diario (ha/día)',
        'Maior desmatamento': 'Mayor deforestación',
        'Maior velocidade': 'Mayor velocidad',
        'Sobreposições (nº de alertas)': 'Superposiciones (nº de alertas)',
        'Embargos e autorizações: consulte o laudo na plataforma.': 'Embargos y autorizaciones: consulte el informe en la plataforma.',
        'Não foi possível carregar a lista de biomas da API ({}). Use uma camada vetorial do bioma como área de interesse.': 'No fue posible cargar la lista de biomas de la API ({}). Use una capa vectorial del bioma como área de interés.',
        # Summary cards and notices
        'Este resumo varia de acordo com os filtros selecionados. Com filtro de fonte ou de cruzamento, o resumo oficial da plataforma não corresponde ao que é baixado: os números passam a ser calculados a partir da camada, e média diária, maior velocidade e sobreposições ficam indisponíveis.': 'Este resumen varía según los filtros seleccionados. Con filtro de fuente o de cruce, el resumen oficial de la plataforma no corresponde a lo que se descarga: los números pasan a calcularse a partir de la capa, y el promedio diario, la mayor velocidad y las superposiciones no están disponibles.',
        'Exportar tabela de atributos (CSV)': 'Exportar tabla de atributos (CSV)',
        'EXPORTAR TABELA DE ATRIBUTOS (CSV)': 'EXPORTAR TABLA DE ATRIBUTOS (CSV)',
        'EXPORTAR INFORMAÇÕES PRINCIPAIS (CSV)': 'EXPORTAR INFORMACIÓN PRINCIPAL (CSV)',
        'Uma linha por alerta, só os campos essenciais: código, área, datas, fonte, bioma, estado e município.': 'Una fila por alerta, solo los campos esenciales: código, área, fechas, fuente, bioma, estado y municipio.',
        'Embargos, autorizações e ações de fiscalização: consulte o laudo na plataforma.': 'Embargos, autorizaciones y acciones de fiscalización: consulte el informe en la plataforma.',
        'Cruzamentos com embargos, autorizações e ações de fiscalização não são exibidos no plugin. Consulte-os no laudo do alerta na plataforma.': 'Los cruces con embargos, autorizaciones y acciones de fiscalización no se muestran en el plugin. Consúltelos en el informe de la alerta en la plataforma.',
        # Chart field names
        'Área do alerta (ha)': 'Área de la alerta (ha)',
        'Área na camada de interesse (ha)': 'Área en la capa de interés (ha)',
        'Percentual na camada de interesse (%)': 'Porcentaje en la capa de interés (%)',
        'Unidade de Conservação': 'Área Protegida',
        'Área em Unidade de Conservação (ha)': 'Área en Área Protegida (ha)',
        'Terra Indígena': 'Territorio Indígena',
        'Área em Terra Indígena (ha)': 'Área en Territorio Indígena (ha)',
        'Área em assentamento (ha)': 'Área en asentamiento (ha)',
        'Área quilombola (ha)': 'Área quilombola (ha)',
        'Reserva da Biosfera': 'Reserva de la Biosfera',
        'Área em Reserva da Biosfera (ha)': 'Área en Reserva de la Biosfera (ha)',
        'Área de manejo (ha)': 'Área de manejo (ha)',
        'Área de proteção integral (ha)': 'Área de protección integral (ha)',
        'Área de uso sustentável (ha)': 'Área de uso sostenible (ha)',
        'Área de APP (ha)': 'Área de APP (ha)',
        'Quantidade de APPs': 'Cantidad de APP',
        'Área de Reserva Legal (ha)': 'Área de Reserva Legal (ha)',
        'Reserva Legal': 'Reserva Legal',
        'Quantidade de Reservas Legais': 'Cantidad de Reservas Legales',
        'Território especial': 'Territorio especial',
        'Área em território especial (ha)': 'Área en territorio especial (ha)',
        'Geoparque': 'Geoparque',
        'Área em geoparque (ha)': 'Área en geoparque (ha)',
        'Proteção integral municipal': 'Protección integral municipal',
        'Área de proteção integral municipal (ha)': 'Área de protección integral municipal (ha)',
        'Uso sustentável municipal': 'Uso sostenible municipal',
        'Área de uso sustentável municipal (ha)': 'Área de uso sostenible municipal (ha)',
        'Proteção integral estadual': 'Protección integral estatal',
        'Área de proteção integral estadual (ha)': 'Área de protección integral estatal (ha)',
        'Uso sustentável estadual': 'Uso sostenible estatal',
        'Área de uso sustentável estadual (ha)': 'Área de uso sostenible estatal (ha)',
        'Quantidade de imóveis rurais': 'Cantidad de inmuebles rurales',
        'Ano': 'Año',
        'Mês': 'Mes',
        'Ano e mês': 'Año y mes',
        'Proteção integral': 'Protección integral',
        'Uso sustentável': 'Uso sostenible',
        'APP': 'APP',
        'Geoparques': 'Geoparques',
        'Áreas por tipo de cruzamento': 'Áreas por tipo de cruce',
        # Result layer names
        'Alertas': 'Alertas',
        'alerta {}': 'alerta {}',
        '{} a {}': '{} a {}',
        'Coordenada {}, {}': 'Coordenada {}, {}',
        # Country names and administrative labels
        'Brasil': 'Brasil',
        'Bolívia': 'Bolivia',
        'Colômbia': 'Colombia',
        'Peru': 'Perú',
        'Indonésia': 'Indonesia',
        'Estado': 'Estado',
        'Departamento': 'Departamento',
        '{} ha/dia': '{} ha/día',
        'Selecione uma camada vetorial': 'Seleccione una capa vectorial',
        'Li e compreendi esta nota informativa.': 'He leído y comprendido esta nota informativa.',
        # Layers tab exports and single-layer analysis
        '<b>Status:</b> Selecione uma camada com pelo menos dois alertas.': '<b>Estado:</b> Seleccione una capa con al menos dos alertas.',
        '<b>Status:</b> A análise exige pelo menos dois alertas.': '<b>Estado:</b> El análisis requiere al menos dos alertas.',
        'Selecione uma camada com pelo menos dois alertas.': 'Seleccione una capa con al menos dos alertas.',
        'TABELA DE ATRIBUTOS (CSV)': 'TABLA DE ATRIBUTOS (CSV)',
        'TABELA DE ATRIBUTOS (XLSX)': 'TABLA DE ATRIBUTOS (XLSX)',
        'CAMADA (GPKG)': 'CAPA (GPKG)',
        'CAMADA (SHP)': 'CAPA (SHP)',
        'Exportar tabela de atributos': 'Exportar tabla de atributos',
        'Exportar camada (com geometria)': 'Exportar capa (con geometría)',
        'ALERTAS DO GRÁFICO': 'ALERTAS DEL GRÁFICO',
        'TABELA DE ATRIBUTOS': 'TABLA DE ATRIBUTOS',
        'CAMADA': 'CAPA',
        'GRÁFICO': 'GRÁFICO',
        'RESUMO': 'RESUMEN',
        'alertas do gráfico': 'alertas del gráfico',
        '{} (gráfico)': '{} (gráfico)',
        'Tabela de atributos': 'Tabla de atributos',
        'Não foi possível exportar o arquivo:\n{}': 'No fue posible exportar el archivo:\n{}',
        # Export buttons
        'EXPORTAR RESUMO (XLSX)': 'EXPORTAR RESUMEN (XLSX)',
        'GRÁFICO (PNG)': 'GRÁFICO (PNG)',
        'ALERTAS DO GRÁFICO (CSV)': 'ALERTAS DEL GRÁFICO (CSV)',
        'ALERTAS DO GRÁFICO (GPKG)': 'ALERTAS DEL GRÁFICO (GPKG)',
        'ALERTAS DO GRÁFICO (SHP)': 'ALERTAS DEL GRÁFICO (SHP)',
        'As exportações desta aba seguem o recorte da análise (campo e valor escolhidos). A tabela completa da camada é exportada na aba Camadas.': 'Las exportaciones de esta pestaña siguen el recorte del análisis (campo y valor elegidos). La tabla completa de la capa se exporta en la pestaña Capas.',
        'Aplique uma análise para exportar os alertas do gráfico.': 'Aplique un análisis para exportar las alertas del gráfico.',
        'Outros ({} grupos)': 'Otros ({} grupos)',
        'Indicador': 'Indicador',
        'Valor': 'Valor',
        'Observação': 'Observación',
        'Não há resumo para exportar.': 'No hay resumen para exportar.',
        'Exportar resumo': 'Exportar resumen',
        'Resumo exportado para:\n{}': 'Resumen exportado a:\n{}',
        # Quick view (WMS)
        "Visualização rápida (sem baixar os polígonos)": "Vista rápida (sin descargar los polígonos)",
        "Mostra os alertas no mapa direto do servidor da plataforma (WMS), "
            "com as estatísticas da API, sem baixar os polígonos — bem mais "
            "rápido em buscas grandes. Detalhes, gráficos, cruzamentos e "
            "exportação precisam da camada completa: use BAIXAR ALERTAS "
            "COMPLETOS depois. Aplica período e área mínima; não aplica filtro "
            "de fonte nem de cruzamento.": (
            "Muestra las alertas en el mapa directamente desde el servidor "
            "de la plataforma (WMS), con las estadísticas de la API, sin "
            "descargar los polígonos: mucho más rápido en búsquedas grandes. "
            "Detalles, gráficos, cruces y exportación necesitan la capa "
            "completa: use DESCARGAR ALERTAS COMPLETAS después. Aplica "
            "período y área mínima; no aplica filtro de fuente ni de cruce."
        ),
        "BAIXAR ALERTAS COMPLETOS": "DESCARGAR ALERTAS COMPLETAS",
        "A visualização rápida não aplica filtro de fonte nem de "
            "cruzamento. Remova esses filtros ou desmarque a visualização "
            "rápida.": (
            "La vista rápida no aplica filtro de fuente ni de cruce. "
            "Quite esos filtros o desmarque la vista rápida."
        ),
        "Nenhum alerta encontrado para os filtros informados.": "No se encontraron alertas para los filtros indicados.",
        "visualização rápida": "vista rápida",
        "Não foi possível abrir a camada do servidor de mapas da "
            "plataforma. Desmarque a visualização rápida para baixar os "
            "alertas pela API.": (
            "No fue posible abrir la capa del servidor de mapas de la "
            "plataforma. Desmarque la vista rápida para descargar las "
            "alertas por la API."
        ),
        "Visualização rápida adicionada: {} alerta(s), {} ha. Para "
            "detalhes, gráficos, cruzamentos ou exportação, clique em "
            "BAIXAR ALERTAS COMPLETOS.": (
            "Vista rápida agregada: {} alerta(s), {} ha. Para detalles, "
            "gráficos, cruces o exportación, haga clic en DESCARGAR "
            "ALERTAS COMPLETAS."
        ),
        "No mapa rápido, o recorte pela camada é aproximado "
            "(retângulo da camada).": (
            "En el mapa rápido, el recorte por la capa es aproximado "
            "(rectángulo de la capa)."
        ),
        # Scope notes (details / CAR search)
        "Atenção: é exibido o alerta inteiro que cruza o imóvel, e não "
        "apenas a parte do alerta dentro do imóvel. Para ver a área do "
        "alerta dentro do imóvel, abra o laudo na plataforma.": (
            "Atención: se muestra la alerta completa que cruza el predio, "
            "y no solo la parte de la alerta dentro del predio. Para ver el "
            "área de la alerta dentro del predio, abra el informe en la "
            "plataforma."
        ),
        "Cruzamentos com embargos e autorizações não são exibidos no "
        "plugin. Consulte-os no laudo do alerta na plataforma.": (
            "Los cruces con embargos y autorizaciones no se muestran en "
            "el plugin. Consúltelos en el informe de la alerta en la "
            "plataforma."
        ),
        # Export dialogs
        "Exportar gráfico": "Exportar gráfico",
        "\n\nO Shapefile corta nomes de campos em 10 caracteres. A "
        "correspondência entre o nome cortado e o nome completo de cada "
        "campo está em:\n{}\n\nUse GeoPackage para manter os nomes "
        "completos.": (
            "\n\nEl Shapefile corta los nombres de campo a 10 caracteres. "
            "La correspondencia entre el nombre cortado y el nombre "
            "completo de cada campo está en:\n{}\n\nUse GeoPackage para "
            "conservar los nombres completos."
        ),
        "Campo no Shapefile": "Campo en el Shapefile",
        "Nome completo": "Nombre completo",
        "Descrição": "Descripción",
        "Exportar estatísticas das camadas": (
            "Exportar estadísticas de las capas"
        ),
        "Exportar dados filtrados": "Exportar datos filtrados",
        "Exportar camada": "Exportar capa",
        "Sem permissão para gravar em:\n{}\n\nEscolha outra pasta "
        "(por exemplo, Documentos ou Área de Trabalho).": (
            "Sin permiso para guardar en:\n{}\n\nElija otra carpeta "
            "(por ejemplo, Documentos o Escritorio)."
        ),
    },
    "en": {
        # Header / country and platform selection
        # "País"/"Idioma" are intentionally not translated here — that
        # label is always fixed in English ("Country"/"Language"), see
        # the comment in main_dialog.py where they're created.
        "Plataforma": "Platform",
        "NOTA INFORMATIVA": "INFORMATION NOTICE",
        "Acesso à API": "API Access",
        "API desconectada": "API disconnected",
        "API conectada como {}": "API connected as {}",
        "API indisponível para {}": "API unavailable for {}",
        # Login
        "E-mail": "Email",
        "E-mail da conta MapBiomas Alerta": "MapBiomas Alerta account email",
        "Senha": "Password",
        "Salvar acesso": "Save credentials",
        "ENTRAR": "SIGN IN",
        "SAIR": "SIGN OUT",
        "Mostrar": "Show",
        "Ocultar": "Hide",
        "Mostrar/ocultar senha": "Show/hide password",
        # Main tabs
        "Nota informativa": "Information notice",
        "Filtros": "Filters",
        "Camadas": "Layers",
        "Estatísticas": "Statistics",
        "Gráficos": "Charts",
        "Detalhes": "Details",
        # Filters tab — sections
        "1. Área de Interesse": "1. AREA OF INTEREST",
        "2. Período": "2. PERIOD",
        "3. Filtros": "3. FILTERS",
        "4. Cruzamentos": "4. CROSSINGS",
        # Area of interest
        "Todo o país selecionado": "Entire selected country",
        "Extensão de uma camada vetorial": "Extent of a vector layer",
        "Informar coordenadas (um ponto)": "Enter coordinates (a point)",
        "Buscar por código do alerta": "Search by alert code",
        "Buscar por imóvel rural (CAR)": (
            "Search by rural property (cadastre)"
        ),
        "Código do alerta": "Alert code",
        "Código do CAR": "Cadastre code",
        "Código numérico do alerta": "Numeric alert code",
        "Código completo do CAR/SICAR": "Full cadastre code",
        "Formato do código CAR válido.": "Valid code format.",
        # Period
        "Filtrar por": "Filter by",
        "Data de detecção": "Detection date",
        "Data de publicação": "Publication date",
        "Data inicial": "Start date",
        "Data final": "End date",
        # Filters
        "Área mínima": "Minimum area",
        "Fontes": "Sources",
        "Todas as fontes": "All sources",
        "Selecionadas": "Selected",
        "Regra das fontes": "Source rule",
        "Qualquer fonte selecionada": "Any selected source",
        "Todas selecionadas juntas": "All selected together",
        "Combinação exata": "Exact combination",
        # Crossings
        "Tipo": "Type",
        "Condição": "Condition",
        "Qualquer cruzamento disponível": "Any available crossing",
        "Conecte-se à API para consultar as opções": (
            "Connect to the API to see the options"
        ),
        "Todos os alertas": "All alerts",
        "Somente alertas com cruzamento": "Only alerts with a crossing",
        "Somente alertas sem cruzamento": "Only alerts without a crossing",
        "Não foi possível consultar os cruzamentos": (
            "Could not query the crossings"
        ),
        "Nenhum cruzamento disponível nesta API": (
            "No crossing available in this API"
        ),
        "Unidades de Conservação (todas)": "Protected Areas (all)",
        "Terras Indígenas": "Indigenous Lands",
        "Assentamentos": "Settlements",
        "Imóveis rurais": "Rural properties",
        # Statistics tab
        "Resumo da consulta": "Search summary",
        "Faça uma consulta para visualizar os resultados.": (
            "Run a search to see the results."
        ),
        "Comparação das camadas de consulta": "Search layer comparison",
        "Alertas encontrados": "Alerts found",
        "Área total": "Total area",
        "Maior alerta": "Largest alert",
        "Código do maior alerta": "Largest alert code",
        "Local do maior alerta": "Largest alert location",
        "Município com maior área": "Municipality with the largest area",
        "Menor alerta": "Smallest alert",
        "Código do menor alerta": "Smallest alert code",
        "Local do menor alerta": "Smallest alert location",
        "Velocidade de desmatamento": "Deforestation speed",
        "Sobreposições com áreas protegidas e institucionais": (
            "Overlaps with protected and institutional areas"
        ),
        "Tipo de data": "Date type",
        "Período analisado": "Period analyzed",
        "EXPORTAR ESTATÍSTICAS (XLSX)": "EXPORT STATISTICS (XLSX)",
        "Análises estatísticas": "Statistical analyses",
        "Camada": "Layer",
        "Alertas": "Alerts",
        "Código": "Code",
        "Período": "Period",
        "Camada 1": "Layer 1",
        "Camada 2 (opcional)": "Layer 2 (optional)",
        "Não comparar": "Don't compare",
        "Barras": "Bar",
        "Pizza": "Pie",
        "Linha": "Line",
        "Número de registros": "Record count",
        "Soma": "Sum",
        "Média": "Average",
        "Separar cada fonte": "Split each source",
        "Agrupar pela combinação": "Group by combination",
        "Todos os valores": "All values",
        "Tipo de gráfico": "Chart type",
        "Campo para comparar": "Field to compare",
        "Cálculo": "Calculation",
        "Campo numérico": "Numeric field",
        "Fontes múltiplas": "Multiple sources",
        "Valor específico": "Specific value",
        "Categorias exibidas": "Categories shown",
        "<b>Status:</b> Aguardando configuração.": (
            "<b>Status:</b> Waiting for configuration."
        ),
        "APLICAR ANÁLISE": "APPLY ANALYSIS",
        # Charts tab
        "Gráficos": "Charts",
        "Os dez maiores grupos são exibidos.": (
            "The ten largest groups are shown."
        ),
        "EXPORTAR GRÁFICO PNG": "EXPORT CHART PNG",
        "EXPORTAR DADOS CSV": "EXPORT DATA CSV",
        "EXPORTAR GPKG": "EXPORT GPKG",
        "EXPORTAR SHP": "EXPORT SHP",
        # Details tab
        "Detalhes do alerta": "Alert details",
        "Identifique um alerta no mapa para consultar imagens e detalhes.": (
            "Identify an alert on the map to view images and details."
        ),
        "IDENTIFICAR ALERTA NO MAPA": "IDENTIFY ALERT ON MAP",
        "Cruzamentos territoriais e ambientais": (
            "Territorial and environmental crossings"
        ),
        "Selecione um alerta para consultar os cruzamentos.": (
            "Select an alert to view its crossings."
        ),
        "Para saber mais sobre cruzamentos existentes, abra o laudo do "
        "alerta na plataforma.": (
            "To learn more about existing crossings, open the alert "
            "report on the platform."
        ),
        "Nenhum imóvel rural informado para este alerta.": (
            "No rural property listed for this alert."
        ),
        "OUTROS ALERTAS NOS MESMOS IMÓVEIS: {}": (
            "OTHER ALERTS ON THE SAME PROPERTIES: {}"
        ),
        "FECHAR ALERTAS RELACIONADOS": "CLOSE RELATED ALERTS",
        "Imagem antes": "Before image",
        "Imagem depois": "After image",
        "Sem imagem": "No image",
        "ABRIR LAUDO NA PLATAFORMA": "OPEN REPORT ON PLATFORM",
        "ANTERIOR": "PREVIOUS",
        "PRÓXIMO": "NEXT",
        "Imóveis cruzados pelo alerta": "Properties crossed by the alert",
        "Outros alertas nos mesmos imóveis": (
            "Other alerts on the same properties"
        ),
        # Validation and error messages
        "O serviço ainda não está configurado.": (
            "The service is not configured yet."
        ),
        "Leia e aceite a nota informativa antes de buscar alertas.": (
            "Read and accept the information notice before searching "
            "for alerts."
        ),
        "Entre na API MapBiomas Alerta antes de realizar a consulta.": (
            "Sign in to the MapBiomas Alerta API before running the "
            "search."
        ),
        "A data inicial não pode ser posterior à data final.": (
            "The start date cannot be later than the end date."
        ),
        "Informe o código do alerta.": "Enter the alert code.",
        "Informe o código do imóvel rural.": (
            "Enter the rural property code."
        ),
        "O código do CAR está fora do padrão esperado. Corrija o valor "
        "indicado antes de realizar a busca.": (
            "The cadastre code is not in the expected format. Fix the "
            "value before running the search."
        ),
        "O código do alerta deve conter somente números.": (
            "The alert code must contain only numbers."
        ),
        "Código CAR reconhecido pela API.": (
            "Cadastre code recognized by the API."
        ),
        "Não existe imóvel com o código informado ou ele não possui "
        "alertas.": (
            "There's no property with the given code, or it has no "
            "alerts."
        ),
        "Não existe alerta com o código informado.": (
            "There's no alert with the given code."
        ),
        "O imóvel informado não possui alertas.": (
            "The given property has no alerts."
        ),
        "Não existe alerta na coordenada indicada.": (
            "There's no alert at the given coordinate."
        ),
        "Não há gráfico para exportar.": "There's no chart to export.",
        "Não foi possível salvar o arquivo PNG.": (
            "Could not save the PNG file."
        ),
        "Não há tabela de estatísticas para exportar.": (
            "There's no statistics table to export."
        ),
        "Não há dados filtrados para exportar.": (
            "There's no filtered data to export."
        ),
        "A camada não possui campos para exportar.": (
            "The layer has no fields to export."
        ),
        "Não há camada de alertas disponível.": (
            "There's no alert layer available."
        ),
        "O alerta selecionado não possui código.": (
            "The selected alert has no code."
        ),
        "A camada não possui alertas.": "The layer has no alerts.",
        "Sem cruzamento": "No crossing",
        "Ex.: -47.9292": "E.g.: -47.9292",
        "Ex.: -15.7801": "E.g.: -15.7801",
        "Disponível apenas quando a consulta é equivalente à da "
        "plataforma (sem recorte manual do mapa, todas as fontes e "
        "sem filtro de cruzamento).": (
            "Only available when the search matches the platform's "
            "own (no manual map clipping, all sources, and no "
            "crossing filter)."
        ),
        "Não há nota informativa configurada para este país.": (
            "No informational notice is configured for this country."
        ),
        "ACESSAR A NOTA INFORMATIVA COMPLETA NA PLATAFORMA": (
            "OPEN THE FULL INFORMATIONAL NOTICE ON THE PLATFORM"
        ),
        "{} com maior área": "{} with largest area",
        "Indisponível: a API não detalhou a área por {}": (
            "Unavailable: the API did not detail the area by {}"
        ),
        "Este país não possui cadastro de imóveis rurais integrado à "
        "plataforma.": (
            "This country does not have a rural property registry "
            "integrated into the platform."
        ),
        "Nenhum cruzamento territorial ou ambiental (Unidade de "
        "Conservação, Terra Indígena, Assentamento etc.) foi "
        "registrado para este alerta. Imóveis rurais cruzados "
        "aparecem em uma seção própria, logo abaixo.": (
            "No territorial or environmental crossing (Protected "
            "Area, Indigenous Land, Settlement etc.) was recorded "
            "for this alert. Crossed rural properties appear in "
            "their own section right below."
        ),
        "A API deste país não disponibilizou campos de cruzamento "
        "compatíveis.": (
            "This country's API did not provide compatible crossing "
            "fields."
        ),
        "Alerta selecionado": "Selected alert",
        "Arquivo CSV (*.csv)": "CSV file (*.csv)",
        "informações principais": "main information",
        "tabela de atributos completa": "full attribute table",
        "Login realizado com sucesso.": "Signed in successfully.",
        "{} alerta(s) carregado(s).": "{} alert(s) loaded.",
        "Exportado em {}": "Exported on {}",
        "Gráfico exportado para:\n{}": "Chart exported to:\n{}",
        "Não foi possível exportar a tabela:\n{}": (
            "Could not export the table:\n{}"
        ),
        "Tabela exportada para:\n{}": "Table exported to:\n{}",
        "Não foi possível exportar o CSV:\n{}": (
            "Could not export the CSV:\n{}"
        ),
        "{} registro(s) — {} — exportado(s) para:\n{}": (
            "{} record(s) — {} — exported to:\n{}"
        ),
        "Configuração alterada. Clique em APLICAR ANÁLISE.": (
            "Configuration changed. Click APPLY ANALYSIS."
        ),
        "<b>Status:</b> Configuração alterada. Clique em "
        "<b>APLICAR ANÁLISE</b>.": (
            "<b>Status:</b> Configuration changed. Click "
            "<b>APPLY ANALYSIS</b>."
        ),
        "<b>Status:</b> Selecione uma camada com pelo menos dois "
        "alertas ou escolha uma segunda camada para comparar.": (
            "<b>Status:</b> Select a layer with at least two alerts, "
            "or choose a second layer to compare."
        ),
        "<b>Status:</b> A análise exige pelo menos dois alertas ou "
        "duas camadas para comparação.": (
            "<b>Status:</b> The analysis requires at least two alerts "
            "or two layers to compare."
        ),
        "Selecione uma camada com pelo menos dois alertas ou escolha "
        "uma segunda camada para comparar.": (
            "Select a layer with at least two alerts, or choose a "
            "second layer to compare."
        ),
        "PROCESSANDO ANÁLISE...": "PROCESSING ANALYSIS...",
        "<b>Status:</b> Processando os registros das camadas...": (
            "<b>Status:</b> Processing the layer records..."
        ),
        "<b>Status:</b> Concluída sem campos analíticos comuns.": (
            "<b>Status:</b> Completed with no common analytical fields."
        ),
        "As camadas não possuem campos analíticos comuns.": (
            "The layers have no common analytical fields."
        ),
        "<b>Status:</b> Análise concluída — {} camada(s), {} "
        "categoria(s), {:.1f} segundo(s).": (
            "<b>Status:</b> Analysis complete — {} layer(s), {} "
            "categorie(s), {:.1f} second(s)."
        ),
        "<b>Status:</b> Análise concluída, mas a configuração "
        "selecionada não produziu dados para o gráfico.": (
            "<b>Status:</b> Analysis complete, but the selected "
            "configuration produced no data for the chart."
        ),
        "<b>Status:</b> Falha ao executar a análise.": (
            "<b>Status:</b> Failed to run the analysis."
        ),
        "Não foi possível aplicar a análise: {}": (
            "Could not apply the analysis: {}"
        ),
        "Área": "Area",
        # Details tab — dynamic messages
        "A sessão expirou antes de carregar o alerta.": (
            "The session expired before the alert could be loaded."
        ),
        "Não foi possível carregar o alerta.": (
            "Could not load the alert."
        ),
        "Alerta {} carregado.": "Alert {} loaded.",
        "Detecção": "Detection",
        "Publicação": "Publication",
        "Fonte(s)": "Source(s)",
        "Bioma(s)": "Biome(s)",
        "Imóvel rural — {}": "Rural property — {}",
        "{} imóvel(is) cruzado(s)": "{} propert(y/ies) crossed",
        "VER {} OUTRO(S) ALERTA(S) E SUAS IMAGENS": (
            "SEE {} OTHER ALERT(S) AND THEIR IMAGES"
        ),
        "Consultando os imóveis relacionados ao alerta...": (
            "Querying the properties related to the alert..."
        ),
        "CONSULTANDO OUTROS ALERTAS...": "QUERYING OTHER ALERTS...",
        "REABRIR OUTROS ALERTAS E SUAS IMAGENS": (
            "REOPEN OTHER ALERTS AND THEIR IMAGES"
        ),
        "OUTROS ALERTAS E IMAGENS ADICIONADOS ABAIXO": (
            "OTHER ALERTS AND IMAGES ADDED BELOW"
        ),
        "Os alertas relacionados e suas imagens já estão carregados.": (
            "The related alerts and their images are already loaded."
        ),
        "Não há uma camada de alertas disponível para esta consulta.": (
            "There's no alert layer available for this search."
        ),
        "Preparando a consulta dos alertas e das imagens...": (
            "Preparing the alert and image search..."
        ),
        "PROCESSANDO OUTROS ALERTAS...": "PROCESSING OTHER ALERTS...",
        "Nenhum outro alerta foi encontrado nos mesmos imóveis.": (
            "No other alert was found on the same properties."
        ),
        "Outros alertas encontrados": "Other alerts found",
        "Imóvel {} — {} outro(s) alerta(s)": (
            "Property {} — {} other alert(s)"
        ),
        "Tipo": "Type",
        "Área do imóvel": "Property area",
        "Carregando alerta {} de {} (código {}) e suas imagens...": (
            "Loading alert {} of {} (code {}) and its images..."
        ),
        "CARREGANDO ALERTA {}/{}...": "LOADING ALERT {}/{}...",
        "Processamento concluído: {} outro(s) alerta(s) e suas "
        "imagens foram carregados.": (
            "Processing complete: {} other alert(s) and their images "
            "were loaded."
        ),
        "Unidades de Conservação": "Protected Areas",
        "Área em Unidade de Conservação": "Area in Protected Area",
        "Área em Terra Indígena": "Area in Indigenous Land",
        "Área em assentamentos": "Area in settlements",
        "Territórios quilombolas": "Quilombola territories",
        "Área quilombola": "Quilombola area",
        "Reservas da Biosfera": "Biosphere Reserves",
        "Área em Reserva da Biosfera": "Area in Biosphere Reserve",
        "Manejo florestal": "Forest management",
        "Área de manejo": "Management area",
        "Proteção integral federal": "Federal integral protection",
        "Área de proteção integral": "Integral protection area",
        "Uso sustentável federal": "Federal sustainable use",
        "Área de uso sustentável": "Sustainable use area",
        "Área de Preservação Permanente": "Permanent Protected Area",
        "APPs": "PPAs",
        "Área de Reserva Legal": "Legal Reserve area",
        "Reservas Legais": "Legal Reserves",
        "Territórios especiais": "Special territories",
        "Área em território especial": "Area in special territory",
        "VER NO MAPA": "SEE ON MAP",
        "Não foi possível carregar as imagens.": (
            "Could not load the images."
        ),
        "Centralizar este alerta no mapa.": "Center this alert on the map.",
        "A API não retornou a geometria deste alerta.": (
            "The API did not return this alert's geometry."
        ),
        "Imagem não disponibilizada pela API.": (
            "Image not made available by the API."
        ),
        "Formato de imagem não reconhecido.": (
            "Unrecognized image format."
        ),
        "O servidor de imagens não respondeu. Tente novamente mais "
        "tarde.": (
            "The image server did not respond. Please try again later."
        ),
        # API error messages (api_client.py)
        "Informe o e-mail e a senha.": "Enter the email and password.",
        "A API não retornou um token de acesso.": (
            "The API did not return an access token."
        ),
        "Faça login na API antes de buscar alertas.": (
            "Sign in to the API before searching for alerts."
        ),
        "A API não informou metadata.totalCount; não é possível "
        "garantir que todos os alertas foram recebidos.": (
            "The API did not report metadata.totalCount; it's not "
            "possible to guarantee all alerts were received."
        ),
        "A paginação informada pela API é inconsistente.": (
            "The pagination reported by the API is inconsistent."
        ),
        "A API entregou mais alertas do que metadata.totalCount. A "
        "consulta foi interrompida para evitar dados incorretos.": (
            "The API delivered more alerts than metadata.totalCount. "
            "The search was stopped to avoid incorrect data."
        ),
        "A consulta estatística da plataforma não informou o total de "
        "alertas. Nenhuma camada foi criada sem essa validação.": (
            "The platform's statistics query did not report the total "
            "number of alerts. No layer was created without this "
            "validation."
        ),
        "A consulta estatística retornou uma área inválida.": (
            "The statistics query returned an invalid area."
        ),
        "A API devolveu um código diferente do solicitado.": (
            "The API returned a different code than requested."
        ),
        "A API não encontrou o alerta informado.": (
            "The API did not find the given alert."
        ),
        "O servidor de imagens está temporariamente indisponível.": (
            "The image server is temporarily unavailable."
        ),
        "O servidor de imagens não respondeu em 30 segundos.": (
            "The image server did not respond within 30 seconds."
        ),
        "A sessão da API não está autenticada.": (
            "The API session is not authenticated."
        ),
        "A consulta à API excedeu 120 segundos.": (
            "The API query exceeded 120 seconds."
        ),
        "A API recusou o acesso (HTTP 403).": (
            "The API refused access (HTTP 403)."
        ),
        "O limite de requisições da API foi atingido (HTTP 429). "
        "Aguarde e tente novamente.": (
            "The API request limit was reached (HTTP 429). Please "
            "wait and try again."
        ),
        "A API retornou uma resposta inválida.": (
            "The API returned an invalid response."
        ),
        "Exportar dados CSV": "Export CSV data",
        "Qual conteúdo você deseja exportar?": (
            "Which content would you like to export?"
        ),
        "Será criado somente um arquivo CSV com a opção escolhida.": (
            "Only one CSV file will be created with the chosen option."
        ),
        "INFORMAÇÕES PRINCIPAIS": "MAIN INFORMATION",
        "TABELA DE ATRIBUTOS COMPLETA": "FULL ATTRIBUTE TABLE",
        "Área (ha)": "Area (ha)",
        "NOTA ACEITA": "NOTICE ACCEPTED",
        "Conectando à API...": "Connecting to the API...",
        "A sessão da API expirou. Entre novamente.": (
            "The API session expired. Please sign in again."
        ),
        "O login foi realizado, mas o QGIS não conseguiu salvar as "
        "credenciais no Gerenciador de Autenticação.": (
            "Signed in, but QGIS could not save the credentials in "
            "the Authentication Manager."
        ),
        "Falha no login automático": "Automatic sign-in failed",
        "Falha na autenticação": "Authentication failed",
        "Sessão expirada": "Session expired",
        "SERVIÇO AINDA NÃO CONFIGURADO": "SERVICE NOT CONFIGURED YET",
        "FAÇA LOGIN PARA BUSCAR": "SIGN IN TO SEARCH",
        "COORDENADAS — UM PONTO": "COORDINATES — ONE POINT",
        "Longitude": "Longitude",
        "Latitude": "Latitude",
        "Sistema de referência: WGS 84 (EPSG:4326)": (
            "Reference system: WGS 84 (EPSG:4326)"
        ),
        "A consulta abrangerá todo o {}. Use período, área mínima e "
        "fontes para limitar o volume.": (
            "The search will cover the entire {}. Use period, minimum "
            "area, and sources to limit the volume."
        ),
        "A validação do formato depende do cadastro do país "
        "selecionado.": (
            "Format validation depends on the selected country's "
            "cadastre."
        ),
        "Formato inválido. Use UF-0000000-"
        "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.": (
            "Invalid format. Use UF-0000000-"
            "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX."
        ),
        "Campo de área não encontrado": "Area field not found",
        "Não aplicado": "Not applied",
        "Data de publicação": "Publication date",
        "Data de detecção": "Detection date",
        "{} até {}": "{} to {}",
        "Média da consulta: {} ha/dia": "Query average: {} ha/day",
        "Maior velocidade: {} ha/dia": "Highest speed: {} ha/day",
        "alerta {}": "alert {}",
        "Unidades de Conservação": "Protected Areas",
        "Terras Indígenas": "Indigenous Lands",
        "Assentamentos": "Settlements",
        "Reservas Legais": "Legal Reserves",
        "Áreas de Preservação Permanente": "Permanent Protected Areas",
        "Manejo Florestal": "Forest Management",
        "Nascentes de Rios": "River Sources",
        "Imóveis Rurais (CAR)": "Rural Properties (cadastre)",
        "Áreas Autorizadas": "Authorized Areas",
        "Ações de Fiscalização": "Enforcement Actions",
        "Escolha as opções e clique em APLICAR ANÁLISE.": (
            "Choose the options and click APPLY ANALYSIS."
        ),
        "Consulta concluída com sucesso.": (
            "Search completed successfully."
        ),
        "A consulta foi concluída, mas nenhum alerta foi encontrado.": (
            "The search is complete, but no alert was found."
        ),
        "A identificação está ativa. Clique em outro alerta no mapa.": (
            "Identification is active. Click another alert on the map."
        ),
        "Clique em um alerta de qualquer camada criada pelo plugin.": (
            "Click an alert from any layer created by the plugin."
        ),
        "A camada não possui o código necessário para consultar o "
        "alerta.": (
            "The layer doesn't have the code needed to query the alert."
        ),
        "Carregando detalhes do alerta {}...": (
            "Loading details for alert {}..."
        ),
        "Todo o {}": "All of {}",
        "Camada vetorial": "Vector layer",
        "Código do alerta{}": "Alert code{}",
        "Imóvel rural{}": "Rural property{}",
        "Coordenadas": "Coordinates",
        "{} · {} · sem filtros adicionais": "{} · {} · no additional filters",
        "{} fonte(s) — {}": "{} source(s) — {}",
        "mín. {} ha": "min. {} ha",
        "{} · {} · {} a {} · {}": "{} · {} · {} to {} · {}",
        "sem período adicional": "no additional period",
        "{}. {} | {} | {} alerta(s)": "{}. {} | {} | {} alert(s)",
        "{} camada(s) filtrada(s).": "{} layer(s) filtered.",
        "Selecione um campo da tabela para realizar a comparação.": (
            "Select a table field to run the comparison."
        ),
        "A camada não possui campos numéricos para este cálculo.": (
            "The layer has no numeric fields for this calculation."
        ),
        # Help texts ("ⓘ" icons)
        "Consulta um alerta específico pelo código da plataforma. "
        "Quando preenchido, o código substitui o recorte espacial.": (
            "Queries a specific alert by the platform's code. When "
            "filled in, the code replaces the spatial extent."
        ),
        "Busca todos os alertas vinculados ao imóvel rural, usando o "
        "código de cadastro (CAR/SICAR) no padrão "
        "UF-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (ex.: "
        "PE-2610905-7821EE203D0441D699AA58725AC25249). Segundo a "
        "documentação oficial da API, essa busca só retorna "
        "resultado para imóveis que já têm pelo menos um alerta — "
        "um código válido mas sem nenhum alerta não gera erro, só "
        "não aparece nada.": (
            "Searches all alerts linked to the rural property, using "
            "the cadastre code (CAR/SICAR) in the pattern "
            "UF-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (e.g., "
            "PE-2610905-7821EE203D0441D699AA58725AC25249). According "
            "to the official API documentation, this search only "
            "returns a result for properties that already have at "
            "least one alert — a valid code with no alerts doesn't "
            "raise an error, it just returns nothing."
        ),
        "Define se o período se aplica à detecção ou à publicação.": (
            "Defines whether the period applies to detection or "
            "publication."
        ),
        "Primeiro dia incluído na consulta.": (
            "First day included in the search."
        ),
        "Último dia incluído na consulta.": (
            "Last day included in the search."
        ),
        "Exclui alertas menores que a área informada, em hectares.": (
            "Excludes alerts smaller than the given area, in hectares."
        ),
        "Selecione uma ou mais fontes de detecção disponibilizadas "
        "pela API.": (
            "Select one or more detection sources made available by "
            "the API."
        ),
        "Define se basta qualquer fonte, se todas devem estar "
        "presentes ou se a combinação deve ser exata.": (
            "Defines whether any source is enough, whether all must "
            "be present, or whether the combination must be exact."
        ),
        "Base territorial ou ambiental usada para verificar "
        "cruzamentos.": (
            "Territorial or environmental base used to check crossings."
        ),
        "Inclui todos os alertas ou somente os que têm ou não têm "
        "cruzamento.": (
            "Includes all alerts, or only those that do or don't have "
            "a crossing."
        ),
        "Define a forma de exibição do resultado na aba Gráficos.": (
            "Defines how the result is displayed on the Charts tab."
        ),
        "Agrupa os alertas pelo atributo escolhido. A opção 'Áreas "
        "por tipo de cruzamento' compara a soma, em hectares, de cada "
        "sobreposição territorial informada pela API; como os tipos "
        "podem se sobrepor, as barras não representam parcelas "
        "exclusivas da área total.": (
            "Groups the alerts by the chosen attribute. The 'Areas by "
            "crossing type' option compares the sum, in hectares, of "
            "each territorial overlap reported by the API; since the "
            "types can overlap, the bars don't represent exclusive "
            "shares of the total area."
        ),
        "Escolhe entre contagem, soma ou média do campo numérico.": (
            "Chooses between count, sum, or average of the numeric "
            "field."
        ),
        "Atributo usado nos cálculos de soma e média.": (
            "Attribute used in the sum and average calculations."
        ),
        "Separa cada fonte ou mantém a combinação registrada no "
        "alerta.": (
            "Splits each source, or keeps the combination recorded in "
            "the alert."
        ),
        "Restringe o gráfico a uma categoria do campo de comparação.": (
            "Restricts the chart to one category of the comparison "
            "field."
        ),
        "Limita quantos grupos do ranking aparecem no gráfico.": (
            "Limits how many ranking groups appear on the chart."
        ),
        "Informe e-mail e senha para acessar a API.": (
            "Enter the email and password to access the API."
        ),
        "Consulta concluída. {} de {} alerta(s) atendem à condição de "
        "cruzamento.": (
            "Search complete. {} of {} alert(s) meet the crossing "
            "condition."
        ),
        "{} alerta(s) foram ignorados por não possuírem geometria "
        "válida.": (
            "{} alert(s) were skipped for not having valid geometry."
        ),
        "Consulta carregada com ressalvas. ": (
            "Search loaded with caveats. "
        ),
        "Consulta por CAR: somente tempo, fontes e métricas de área "
        "com dados válidos podem ser analisados.": (
            "Cadastre search: only time, sources, and area metrics "
            "with valid data can be analyzed."
        ),
        "Consulta por coordenada: somente tempo, fontes e métricas de "
        "área com dados válidos podem ser analisados.": (
            "Coordinate search: only time, sources, and area metrics "
            "with valid data can be analyzed."
        ),
        "Esta combinação não pode ser calculada com precisão com os "
        "campos fornecidos pela API. Use Número de registros.": (
            "This combination cannot be calculated precisely with the "
            "fields provided by the API. Use Record count."
        ),
        "Faça uma consulta para visualizar as estatísticas.": (
            "Run a search to see the statistics."
        ),
        "Consultar novamente a nota informativa do país selecionado.": (
            "Check the selected country's information notice again."
        ),
        "Identifique um alerta no mapa para consultar imagens e "
        "detalhes.": (
            "Identify an alert on the map to view images and details."
        ),
        " de {}": " of {}",
        "Cada barra soma a área numérica informada pela API para o "
        "respectivo tipo de cruzamento. Os tipos podem se sobrepor; "
        "não some as barras como se fossem área exclusiva.": (
            "Each bar sums the numeric area reported by the API for "
            "the respective crossing type. Types can overlap; don't "
            "add up the bars as if they were exclusive area."
        ),
        "Resultado agregado pela API para os mesmos filtros da "
        "camada.": (
            "Result aggregated by the API for the same layer filters."
        ),
        "Áreas individualizadas por território apenas quando há "
        "alocação exata na API ou interseção geométrica com cada "
        "feição da camada selecionada.": (
            "Areas broken down by territory only when there's an "
            "exact allocation in the API or a geometric intersection "
            "with each feature of the selected layer."
        ),
        "Alertas com múltiplas fontes aparecem uma vez em cada "
        "fonte; a soma das categorias pode superar o total da "
        "consulta.": (
            "Alerts with multiple sources appear once per source; the "
            "sum of the categories can exceed the search total."
        ),
        "Um alerta pode aparecer em mais de uma categoria "
        "territorial.": (
            "An alert can appear in more than one territorial category."
        ),
        "{}: {}{} por {}{}. Exibindo {} grupo(s). {}": (
            "{}: {}{} by {}{}. Showing {} group(s). {}"
        ),
        "Comparação entre duas camadas": "Comparison between two layers",
        "Ranking": "Ranking",
        "tipo de cruzamento": "crossing type",
        " — filtro: {}": " — filter: {}",
        "ABRIR PASTA": "OPEN FOLDER",
        "Não foi possível verificar os cruzamentos disponíveis para {} "
        "— tente novamente mais tarde.": (
            "Could not verify the available crossings for {} — try "
            "again later."
        ),
        "LI E CONCORDO": "I HAVE READ AND AGREE",
        "Consulta e análise de alertas de desmatamento no QGIS": (
            "Deforestation alert search and analysis for QGIS"
        ),
        "ENTRAR NA API": "SIGN IN TO THE API",
        "Salvar acesso no QGIS": "Save credentials in QGIS",
        "Manter acesso salvo neste perfil do QGIS": (
            "Keep credentials saved in this QGIS profile"
        ),
        "As credenciais serão protegidas pelo Gerenciador de "
        "Autenticação do QGIS.": (
            "The credentials will be protected by the QGIS "
            "Authentication Manager."
        ),
        "Selecione uma camada vetorial.": "Select a vector layer.",
        "{} feição(ões) na camada.": "{} feature(s) in the layer.",
        "{} a {}": "{} to {}",
        "Bioma": "Biome",
        "Fonte": "Source",
        "Área do alerta": "Alert area",
        "Define o recorte espacial da busca: todo o país selecionado, "
        "uma camada vetorial já carregada, um ponto por coordenadas, "
        "um alerta específico pelo código, ou um imóvel rural pelo "
        "código do cadastro.": (
            "Defines the search's spatial extent: the entire selected "
            "country, an already-loaded vector layer, a point by "
            "coordinates, a specific alert by its code, or a rural "
            "property by its cadastre code."
        ),
        "Para acessar a API é necessário ter um login cadastrado na "
        "plataforma MapBiomas Alerta do país selecionado. Se ainda "
        "não tiver uma conta, cadastre-se no site oficial antes de "
        "entrar aqui.": (
            "To access the API you need a registered login on the "
            "MapBiomas Alerta platform for the selected country. If "
            "you don't have an account yet, sign up on the official "
            "site before signing in here."
        ),
        "Acesse: {}": "Visit: {}",
        "Incluir dados de cruzamento territorial na camada": (
            "Include territorial crossing data in the layer"
        ),
        "O período selecionado tem mais de 1 ano. Reduza o intervalo "
        "de datas — se precisar de um período maior, faça mais de "
        "uma busca (uma para cada ano, por exemplo).": (
            "The selected period is longer than 1 year. Narrow the "
            "date range — if you need a longer period, run more than "
            "one search (one per year, for example)."
        ),
        "Esta busca deve retornar aproximadamente {} alertas e pode "
        "demorar um pouco. Períodos mais curtos deixam a busca mais "
        "rápida.": (
            "This search should return approximately {} alerts and "
            "may take a while. Shorter periods make the search "
            "faster."
        ),
        "Desmarque para buscas mais rápidas quando você não precisa "
        "dos detalhes de cruzamento (Unidade de Conservação, Terra "
        "Indígena, Assentamento etc.) — o filtro de Cruzamentos "
        "continua funcionando normalmente mesmo desmarcado. Com a "
        "opção desmarcada, a aba Detalhes de cada alerta continua "
        "mostrando os cruzamentos normalmente (ela já consulta isso "
        "à parte, por alerta), mas a exportação 'Tabela de atributos "
        "completa', 'Cruzamentos territoriais' e o gráfico 'Áreas "
        "por tipo de cruzamento' ficam indisponíveis para essa "
        "camada — refaça a busca com a opção marcada se precisar "
        "deles depois.": (
            "Uncheck for faster searches when you don't need the "
            "crossing details (Protected Area, Indigenous Land, "
            "Settlement etc.) — the Crossings filter still works "
            "normally even when unchecked. With the option "
            "unchecked, the Details tab for each alert still shows "
            "its crossings normally (it already queries that "
            "separately, per alert), but the 'Full attribute table' "
            "and 'Territorial crossings' exports and the 'Areas by "
            "crossing type' chart become unavailable for that layer "
            "— redo the search with the option checked if you need "
            "them later."
        ),
        "Não foi possível exportar a camada:\n{}": (
            "Could not export the layer:\n{}"
        ),
        "A camada espacial foi exportada, mas a tabela de cruzamentos "
        "falhou:\n{}": (
            "The spatial layer was exported, but the crossings table "
            "failed:\n{}"
        ),
        "A camada espacial foi exportada, mas o CSV de cruzamentos "
        "falhou:\n{}": (
            "The spatial layer was exported, but the crossings CSV "
            "failed:\n{}"
        ),
        "Camada exportada para:\n{}": "Layer exported to:\n{}",
        "\n\nCruzamentos: tabela interna 'cruzamentos' no GeoPackage.": (
            "\n\nCrossings: internal 'cruzamentos' table in the "
            "GeoPackage."
        ),
        "\n\nCruzamentos (formato longo, um por linha): {}": (
            "\n\nCrossings (long format, one per row): {}"
        ),
        "\n\nVeja {} para entender a diferença entre as tabelas (a de "
        "cruzamentos tem muito mais linhas — isso é esperado).": (
            "\n\nSee {} to understand the difference between the "
            "tables (the crossings one has many more rows — that's "
            "expected)."
        ),
        "\n\nObservação: o Shapefile limita nomes de campos. Use "
        "GeoPackage quando precisar preservar melhor a estrutura.": (
            "\n\nNote: Shapefile limits field names. Use GeoPackage "
            "when you need to better preserve the structure."
        ),
        # Layers tab
        "Camada de alertas": "Alert layer",
        "Nenhuma consulta realizada.": "No search performed yet.",
        "Escolha qual camada de consulta alimenta o gráfico.": (
            "Choose which search layer feeds the chart."
        ),
        "Nenhuma camada filtrada.": "No filtered layer.",
        "Abrir tabela de atributos": "Open attribute table",
        "Remover camada": "Remove layer",
        "Exportar camada em CSV": "Export layer as CSV",
        "Conteúdo do arquivo": "File content",
        "Informações principais": "Main information",
        "Tabela de atributos completa": "Full attribute table",
        "EXPORTAR CSV": "EXPORT CSV",
        (
            "Existem 3 formatos porque cada um responde uma pergunta "
            "diferente:\n\n"
            "• Informações principais — 1 linha por alerta, só os "
            "campos essenciais (código, área, data, bioma/estado/"
            "município). O jeito mais simples de olhar a lista de "
            "alertas.\n\n"
            "• Tabela de atributos completa — 1 linha por alerta, com "
            "TODOS os campos da camada. A divisão de área por "
            "território (UC, TI, assentamento etc.) vem dentro de "
            "colunas com texto em JSON, então cada alerta ainda ocupa "
            "só 1 linha, mesmo cruzando vários territórios.\n\n"
            "• Cruzamentos territoriais — formato longo: 1 linha para "
            "CADA território que cada alerta cruza. Um único alerta que "
            "cruza 3 territórios diferentes gera 3 linhas aqui. Por "
            "isso esta tabela sempre tem MUITO mais linhas que as "
            "outras duas — não é duplicação nem erro, é o mesmo dado "
            "reorganizado para ser fácil de somar, filtrar ou cruzar "
            "com outras planilhas, já sem o JSON."
        ): (
            "There are 3 formats because each one answers a different "
            "question:\n\n"
            "• Main information — 1 row per alert, only the essential "
            "fields (code, area, date, biome/state/municipality). The "
            "simplest way to look at the alert list.\n\n"
            "• Full attribute table — 1 row per alert, with ALL the "
            "layer's fields. The area breakdown by territory (UC, TI, "
            "settlement etc.) comes inside columns with JSON text, so "
            "each alert still takes up only 1 row, even when it "
            "crosses several territories.\n\n"
            "• Territorial crossings — long format: 1 row for EACH "
            "territory each alert crosses. A single alert crossing 3 "
            "different territories generates 3 rows here. That's why "
            "this table always has MANY more rows than the other two "
            "— it's not duplication or an error, it's the same data "
            "reorganized to be easy to sum, filter, or cross with "
            "other spreadsheets, already without the JSON."
        ),
        # Main buttons
        "BUSCAR ALERTAS": "SEARCH ALERTS",
        "LIMPAR": "CLEAR",
        "CANCELAR": "CANCEL",
        "BAIXANDO...": "DOWNLOADING...",
        "CONSULTANDO RESUMO...": "FETCHING SUMMARY...",
        "BAIXANDO {}/{}...": "DOWNLOADING {}/{}...",
        "PROCESSANDO {}/{}...": "PROCESSING {}/{}...",
        "FINALIZANDO...": "FINISHING...",
        # Biome filter / chart window / layer category
        'Todos os biomas': 'All biomes',
        'Limita a busca a um ou mais biomas, sem precisar carregar uma camada vetorial. A lista vem da própria API da plataforma.': "Limits the search to one or more biomes, without loading a vector layer. The list comes from the platform's own API.",
        'AMPLIAR GRÁFICO': 'ENLARGE CHART',
        'Gráfico': 'Chart',
        'FECHAR': 'CLOSE',
        'Não há gráfico para exibir.': 'There is no chart to show.',
        'A camada representa': 'The layer represents',
        'Detectar automaticamente': 'Detect automatically',
        'Terra indígena': 'Indigenous land',
        'Unidade de conservação': 'Conservation unit',
        'Território quilombola': 'Quilombola territory',
        'Município': 'Municipality',
        'Estado / departamento': 'State / department',
        'Assentamento': 'Settlement',
        'Define o tipo de território da camada escolhida, usado para nomear a categoria nas tabelas de cruzamento e nas exportações. No modo automático, o plugin tenta reconhecer pelo nome da camada e depois pelos campos.': 'Sets the territory type of the chosen layer, used to name the category in the crossing tables and exports. In automatic mode, the plugin tries to recognize it from the layer name, then from its fields.',
        # Panel layout
        'Todo o país': 'Whole country',
        'Coordenada (ponto)': 'Coordinate (point)',
        'Imóvel rural (CAR)': 'Rural property (CAR)',
        'Últimos 30 dias': 'Last 30 days',
        '90 dias': '90 days',
        'Este ano': 'This year',
        '⤢ AMPLIAR': '⤢ ENLARGE',
        'Abre o gráfico numa janela maior, com todas as categorias.': 'Opens the chart in a larger window, with every category.',
        'área ≥ {} ha': 'area ≥ {} ha',
        'com dados de cruzamento': 'with crossing data',
        'sem dados de cruzamento': 'without crossing data',
        # Panel layout (continued)
        'Um ou mais biomas, sem precisar carregar uma camada vetorial.': 'One or more biomes, without loading a vector layer.',
        'Selecione um ou mais biomas': 'Select one or more biomes',
        'Limita a busca aos biomas escolhidos. O recorte é feito pela própria API da plataforma, com contagem e área exatas.': "Limits the search to the chosen biomes. The clipping is done by the platform's own API, with exact counts and area.",
        'Entre na API para carregar a lista de biomas.': 'Sign in to the API to load the list of biomes.',
        'A API deste país não informou a lista de biomas. Use uma camada vetorial do bioma como área de interesse.': "This country's API did not provide the list of biomes. Use a vector layer of the biome as the area of interest.",
        'Selecione ao menos um bioma para a busca.': 'Select at least one biome for the search.',
        'Camada vetorial já carregada no QGIS cuja geometria define o recorte da busca.': 'Vector layer already loaded in QGIS whose geometry defines the search area.',
        'Selecione um alerta para ver os imóveis cruzados.': 'Select an alert to see the crossed properties.',
        'Visualização rápida no mapa': 'Quick map view',
        'Mostra os alertas no mapa direto do servidor da plataforma, com as estatísticas da API, sem baixar os polígonos. Os polígonos só são baixados, automaticamente, quando você exporta, gera um gráfico ou abre os detalhes de um alerta. Com filtro de fonte ou de cruzamento, a busca baixa os polígonos direto.': "Shows the alerts on the map straight from the platform's server, with the API statistics, without downloading the polygons. Polygons are only downloaded, automatically, when you export, build a chart or open an alert's details. With a source or crossing filter, the search downloads the polygons directly.",
        'Visualização rápida indisponível ({}). Baixando os alertas pela API.': 'Quick view unavailable ({}). Downloading the alerts through the API.',
        '{} alerta(s), {} ha — mostrados no mapa sem baixar os polígonos. Eles serão baixados automaticamente se você exportar, gerar um gráfico ou abrir os detalhes de um alerta. Alertas pequenos podem não aparecer em escalas muito pequenas: aproxime o mapa.': "{} alert(s), {} ha — shown on the map without downloading the polygons. They will be downloaded automatically if you export, build a chart or open an alert's details. Small alerts may not show at very small scales: zoom in.",
        'Baixando os polígonos dos alertas para esta ação...': 'Downloading the alert polygons for this action...',
        '{} ha': '{} ha',
        'até': 'to',
        'a camada do servidor não permite filtrar por bioma': "the server layer can't filter by biome",
        'o servidor de mapas não respondeu': 'the map server did not respond',
        'nenhuma camada de alertas publicada no servidor de mapas': 'no alert layer published on the map server',
        # Search progress and summary
        'Baixando os alertas...': 'Downloading the alerts...',
        'Os números abaixo já são os oficiais da plataforma para estes filtros. A camada aparece no mapa ao terminar.': "The numbers below are already the platform's official figures for these filters. The layer shows on the map when it finishes.",
        'Números da plataforma para o retângulo da camada; ao terminar, são recalculados com o recorte exato.': "Platform figures for the layer's bounding rectangle; when it finishes, they are recalculated with the exact clip.",
        'Baixando os alertas… página {} de {}': 'Downloading the alerts… page {} of {}',
        'Total de alertas': 'Total alerts',
        'Área desmatada (ha)': 'Deforested area (ha)',
        'Média diária (ha/dia)': 'Daily average (ha/day)',
        'Maior desmatamento': 'Largest deforestation',
        'Maior velocidade': 'Highest speed',
        'Sobreposições (nº de alertas)': 'Overlaps (no. of alerts)',
        'Embargos e autorizações: consulte o laudo na plataforma.': 'Embargoes and authorizations: see the report on the platform.',
        'Não foi possível carregar a lista de biomas da API ({}). Use uma camada vetorial do bioma como área de interesse.': 'Could not load the list of biomes from the API ({}). Use a vector layer of the biome as the area of interest.',
        # Summary cards and notices
        'Este resumo varia de acordo com os filtros selecionados. Com filtro de fonte ou de cruzamento, o resumo oficial da plataforma não corresponde ao que é baixado: os números passam a ser calculados a partir da camada, e média diária, maior velocidade e sobreposições ficam indisponíveis.': "This summary depends on the selected filters. With a source or crossing filter, the platform's official summary doesn't match what is downloaded: the figures are computed from the layer, and daily average, highest speed and overlaps are unavailable.",
        'Exportar tabela de atributos (CSV)': 'Export attribute table (CSV)',
        'EXPORTAR TABELA DE ATRIBUTOS (CSV)': 'EXPORT ATTRIBUTE TABLE (CSV)',
        'EXPORTAR INFORMAÇÕES PRINCIPAIS (CSV)': 'EXPORT MAIN INFORMATION (CSV)',
        'Uma linha por alerta, só os campos essenciais: código, área, datas, fonte, bioma, estado e município.': 'One row per alert, essential fields only: code, area, dates, source, biome, state and municipality.',
        'Embargos, autorizações e ações de fiscalização: consulte o laudo na plataforma.': 'Embargoes, authorizations and enforcement actions: see the report on the platform.',
        'Cruzamentos com embargos, autorizações e ações de fiscalização não são exibidos no plugin. Consulte-os no laudo do alerta na plataforma.': 'Crossings with embargoes, authorizations and enforcement actions are not shown in the plugin. Check them in the alert report on the platform.',
        # Chart field names
        'Área do alerta (ha)': 'Alert area (ha)',
        'Área na camada de interesse (ha)': 'Area in the layer of interest (ha)',
        'Percentual na camada de interesse (%)': 'Percentage in the layer of interest (%)',
        'Unidade de Conservação': 'Protected Area',
        'Área em Unidade de Conservação (ha)': 'Area in Protected Area (ha)',
        'Terra Indígena': 'Indigenous Land',
        'Área em Terra Indígena (ha)': 'Area in Indigenous Land (ha)',
        'Área em assentamento (ha)': 'Area in settlement (ha)',
        'Área quilombola (ha)': 'Quilombola area (ha)',
        'Reserva da Biosfera': 'Biosphere Reserve',
        'Área em Reserva da Biosfera (ha)': 'Area in Biosphere Reserve (ha)',
        'Área de manejo (ha)': 'Management area (ha)',
        'Área de proteção integral (ha)': 'Integral protection area (ha)',
        'Área de uso sustentável (ha)': 'Sustainable use area (ha)',
        'Área de APP (ha)': 'APP area (ha)',
        'Quantidade de APPs': 'Number of APPs',
        'Área de Reserva Legal (ha)': 'Legal Reserve area (ha)',
        'Reserva Legal': 'Legal Reserve',
        'Quantidade de Reservas Legais': 'Number of Legal Reserves',
        'Território especial': 'Special territory',
        'Área em território especial (ha)': 'Area in special territory (ha)',
        'Geoparque': 'Geopark',
        'Área em geoparque (ha)': 'Area in geopark (ha)',
        'Proteção integral municipal': 'Municipal integral protection',
        'Área de proteção integral municipal (ha)': 'Municipal integral protection area (ha)',
        'Uso sustentável municipal': 'Municipal sustainable use',
        'Área de uso sustentável municipal (ha)': 'Municipal sustainable use area (ha)',
        'Proteção integral estadual': 'State integral protection',
        'Área de proteção integral estadual (ha)': 'State integral protection area (ha)',
        'Uso sustentável estadual': 'State sustainable use',
        'Área de uso sustentável estadual (ha)': 'State sustainable use area (ha)',
        'Quantidade de imóveis rurais': 'Number of rural properties',
        'Ano': 'Year',
        'Mês': 'Month',
        'Ano e mês': 'Year and month',
        'Proteção integral': 'Integral protection',
        'Uso sustentável': 'Sustainable use',
        'APP': 'APP',
        'Geoparques': 'Geoparks',
        'Áreas por tipo de cruzamento': 'Areas by crossing type',
        # Result layer names
        'Alertas': 'Alerts',
        'alerta {}': 'alert {}',
        '{} a {}': '{} to {}',
        'Coordenada {}, {}': 'Coordinate {}, {}',
        # Country names and administrative labels
        'Brasil': 'Brazil',
        'Bolívia': 'Bolivia',
        'Colômbia': 'Colombia',
        'Peru': 'Peru',
        'Indonésia': 'Indonesia',
        'Estado': 'State',
        'Departamento': 'Department',
        '{} ha/dia': '{} ha/day',
        'Selecione uma camada vetorial': 'Select a vector layer',
        'Li e compreendi esta nota informativa.': 'I have read and understood this information notice.',
        # Layers tab exports and single-layer analysis
        '<b>Status:</b> Selecione uma camada com pelo menos dois alertas.': '<b>Status:</b> Select a layer with at least two alerts.',
        '<b>Status:</b> A análise exige pelo menos dois alertas.': '<b>Status:</b> The analysis requires at least two alerts.',
        'Selecione uma camada com pelo menos dois alertas.': 'Select a layer with at least two alerts.',
        'TABELA DE ATRIBUTOS (CSV)': 'ATTRIBUTE TABLE (CSV)',
        'TABELA DE ATRIBUTOS (XLSX)': 'ATTRIBUTE TABLE (XLSX)',
        'CAMADA (GPKG)': 'LAYER (GPKG)',
        'CAMADA (SHP)': 'LAYER (SHP)',
        'Exportar tabela de atributos': 'Export attribute table',
        'Exportar camada (com geometria)': 'Export layer (with geometry)',
        'ALERTAS DO GRÁFICO': 'CHART ALERTS',
        'TABELA DE ATRIBUTOS': 'ATTRIBUTE TABLE',
        'CAMADA': 'LAYER',
        'GRÁFICO': 'CHART',
        'RESUMO': 'SUMMARY',
        'alertas do gráfico': 'chart alerts',
        '{} (gráfico)': '{} (chart)',
        'Tabela de atributos': 'Attribute table',
        'Não foi possível exportar o arquivo:\n{}': 'Could not export the file:\n{}',
        # Export buttons
        'EXPORTAR RESUMO (XLSX)': 'EXPORT SUMMARY (XLSX)',
        'GRÁFICO (PNG)': 'CHART (PNG)',
        'ALERTAS DO GRÁFICO (CSV)': 'CHART ALERTS (CSV)',
        'ALERTAS DO GRÁFICO (GPKG)': 'CHART ALERTS (GPKG)',
        'ALERTAS DO GRÁFICO (SHP)': 'CHART ALERTS (SHP)',
        'As exportações desta aba seguem o recorte da análise (campo e valor escolhidos). A tabela completa da camada é exportada na aba Camadas.': "Exports in this tab follow the analysis cut (chosen field and value). The layer's full table is exported in the Layers tab.",
        'Aplique uma análise para exportar os alertas do gráfico.': "Apply an analysis to export the chart's alerts.",
        'Outros ({} grupos)': 'Others ({} groups)',
        'Indicador': 'Indicator',
        'Valor': 'Value',
        'Observação': 'Note',
        'Não há resumo para exportar.': 'There is no summary to export.',
        'Exportar resumo': 'Export summary',
        'Resumo exportado para:\n{}': 'Summary exported to:\n{}',
        # Quick view (WMS)
        "Visualização rápida (sem baixar os polígonos)": "Quick view (no polygon download)",
        "Mostra os alertas no mapa direto do servidor da plataforma (WMS), "
            "com as estatísticas da API, sem baixar os polígonos — bem mais "
            "rápido em buscas grandes. Detalhes, gráficos, cruzamentos e "
            "exportação precisam da camada completa: use BAIXAR ALERTAS "
            "COMPLETOS depois. Aplica período e área mínima; não aplica filtro "
            "de fonte nem de cruzamento.": (
            "Shows the alerts on the map straight from the platform's map "
            "server (WMS), with the API statistics, without downloading the "
            "polygons — much faster for large searches. Details, charts, "
            "crossings and export need the full layer: use DOWNLOAD FULL "
            "ALERTS afterwards. Applies period and minimum area; does not "
            "apply source or crossing filters."
        ),
        "BAIXAR ALERTAS COMPLETOS": "DOWNLOAD FULL ALERTS",
        "A visualização rápida não aplica filtro de fonte nem de "
            "cruzamento. Remova esses filtros ou desmarque a visualização "
            "rápida.": (
            "Quick view does not apply source or crossing filters. Remove "
            "those filters or uncheck quick view."
        ),
        "Nenhum alerta encontrado para os filtros informados.": "No alerts found for the given filters.",
        "visualização rápida": "quick view",
        "Não foi possível abrir a camada do servidor de mapas da "
            "plataforma. Desmarque a visualização rápida para baixar os "
            "alertas pela API.": (
            "Could not open the platform's map server layer. Uncheck quick "
            "view to download the alerts through the API."
        ),
        "Visualização rápida adicionada: {} alerta(s), {} ha. Para "
            "detalhes, gráficos, cruzamentos ou exportação, clique em "
            "BAIXAR ALERTAS COMPLETOS.": (
            "Quick view added: {} alert(s), {} ha. For details, charts, "
            "crossings or export, click DOWNLOAD FULL ALERTS."
        ),
        "No mapa rápido, o recorte pela camada é aproximado "
            "(retângulo da camada).": (
            "In the quick map, clipping by the layer is approximate (the "
            "layer's bounding rectangle)."
        ),
        # Scope notes (details / CAR search)
        "Atenção: é exibido o alerta inteiro que cruza o imóvel, e não "
        "apenas a parte do alerta dentro do imóvel. Para ver a área do "
        "alerta dentro do imóvel, abra o laudo na plataforma.": (
            "Note: the whole alert that crosses the property is shown, "
            "not only the part of the alert inside the property. To see "
            "the alert area inside the property, open the report on the "
            "platform."
        ),
        "Cruzamentos com embargos e autorizações não são exibidos no "
        "plugin. Consulte-os no laudo do alerta na plataforma.": (
            "Crossings with embargoes and authorizations are not shown "
            "in the plugin. Check them in the alert report on the "
            "platform."
        ),
        # Export dialogs
        "Exportar gráfico": "Export chart",
        "\n\nO Shapefile corta nomes de campos em 10 caracteres. A "
        "correspondência entre o nome cortado e o nome completo de cada "
        "campo está em:\n{}\n\nUse GeoPackage para manter os nomes "
        "completos.": (
            "\n\nShapefile cuts field names to 10 characters. The mapping "
            "between each shortened name and the full field name is "
            "in:\n{}\n\nUse GeoPackage to keep the full names."
        ),
        "Campo no Shapefile": "Shapefile field",
        "Nome completo": "Full name",
        "Descrição": "Description",
        "Exportar estatísticas das camadas": "Export layer statistics",
        "Exportar dados filtrados": "Export filtered data",
        "Exportar camada": "Export layer",
        "Sem permissão para gravar em:\n{}\n\nEscolha outra pasta "
        "(por exemplo, Documentos ou Área de Trabalho).": (
            "No permission to write to:\n{}\n\nChoose another folder "
            "(for example, Documents or Desktop)."
        ),
    },
}


class Translator:
    """Holds the current UI language and translates text on demand.

    Usage: self.translator.tr("Filtros") -> "Filtros"/"Filters"
    depending on the selected language. Falls back to the original
    Portuguese text if no translation is registered.
    """

    def __init__(self, language="pt"):
        self.language = language if language in LANGUAGE_NAMES else "pt"

    def set_language(self, language):
        self.language = language if language in LANGUAGE_NAMES else "pt"

    def tr(self, text, *format_args):
        if self.language != "pt":
            text = TRANSLATIONS.get(self.language, {}).get(text, text)
        if format_args:
            try:
                return text.format(*format_args)
            except (IndexError, KeyError, ValueError):
                return text
        return text
