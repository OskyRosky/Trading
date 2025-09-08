Algo Trading System – From Data to Execution

Introducción

Este repositorio tiene como propósito documentar y desarrollar un sistema completo de trading algorítmico, construido desde cero. El objetivo es crear un flujo de trabajo que permita adquirir datos de mercado, analizarlos, diseñar y probar estrategias, ejecutar operaciones automáticamente en Binance y monitorear el estado del sistema de forma continua.

El proyecto se basa en un enfoque modular, donde cada etapa cumple un objetivo específico y contribuye al funcionamiento global.

⸻

Etapa 0: Definición del objetivo

La primera etapa consiste en establecer el propósito del sistema de trading algorítmico. En este caso, se busca automatizar la toma de decisiones de trading, reducir la intervención manual y asegurar un control de riesgo constante. La definición conceptual del sistema sirve como guía para las fases siguientes, ya que permite tener claridad sobre lo que se pretende construir y los resultados que se esperan alcanzar.

Objetivo: definir el propósito central del sistema y los criterios de éxito que guiarán su desarrollo.

⸻

Etapa 1: Adquisición y almacenamiento de datos

En primer lugar, el sistema debe contar con datos de mercado confiables. Para ello, se descargan diariamente precios históricos y recientes desde Binance, tanto en intervalos diarios como de cuatro horas. Posteriormente, los datos se almacenan en un Data Lake en formato Parquet, organizado por símbolo, intervalo y fecha. Para consultas iniciales se emplea DuckDB, por su rapidez y simplicidad, aunque se contempla la posibilidad de utilizar Postgres o TimescaleDB en fases posteriores.

Objetivo: asegurar la existencia de un repositorio central de datos estructurado, optimizado y preparado para análisis futuros.

⸻

Etapa 2: Procesamiento y análisis

Seguidamente, los datos almacenados pasan por un proceso de validación y limpieza. Esto incluye la detección de duplicados, la verificación de consistencia entre precios open-high-low-close y la normalización temporal en UTC. Luego se generan indicadores técnicos (RSI, MACD, medias móviles, entre otros) que enriquecen el dataset. En este punto también se pueden integrar fuentes externas como noticias o indicadores macroeconómicos.

Objetivo: transformar los datos crudos en información lista para alimentar estrategias y modelos de trading.

⸻

Etapa 3: Modelos y backtesting

Luego de tener la información procesada, se desarrollan y prueban distintas estrategias. Se consideran tanto modelos basados en machine learning o deep learning como reglas técnicas tradicionales. Las estrategias son validadas a través de backtesting sobre datos históricos, evaluando métricas como ratio de Sharpe, drawdown máximo, tasa de acierto y beneficio esperado.

Objetivo: evaluar la viabilidad de las estrategias antes de aplicarlas en un entorno real.

⸻

Etapa 4: Ejecución automática en vivo

Una vez que las estrategias han sido validadas, el sistema convierte las señales en órdenes concretas que se envían automáticamente a Binance a través de su API. Además, se aplican reglas de gestión de riesgo como el tamaño de posición, la colocación de stop-loss y take-profit, y la activación de un kill switch en caso de que el drawdown supere un límite definido.

Objetivo: automatizar la ejecución de operaciones en el mercado de acuerdo con las estrategias, manteniendo un control estricto del riesgo.

⸻

Etapa 5: Monitoreo y orquestación

Seguidamente, el sistema necesita monitorear todos sus procesos para garantizar que estén funcionando correctamente. Un orquestador como Prefect o Airflow se encarga de programar y ejecutar las tareas de ingesta de datos y análisis. Paralelamente, n8n permite manejar integraciones con señales externas (ejemplo: TradingView), generar alertas en tiempo real (Telegram, Discord) y supervisar endpoints de salud del sistema.

Objetivo: asegurar que cada componente del sistema se ejecute de manera confiable y emitir alertas en caso de anomalías.

⸻

Etapa 6: Integración de inteligencia externa

Una vez establecidas las bases del sistema, se pueden integrar fuentes de inteligencia externas. Entre ellas se incluyen APIs como OpenAI para generar resúmenes de noticias y detectar eventos macroeconómicos relevantes. También se pueden crear agentes inteligentes en n8n que combinen señales técnicas con contexto externo para enriquecer las decisiones del bot.

Objetivo: ampliar la visión del sistema incorporando información externa que complemente los modelos técnicos.

⸻

Etapa 7: Observabilidad y reporting

Finalmente, el sistema debe proporcionar transparencia y trazabilidad. Se definen métricas clave como PnL, drawdown, número de operaciones y tasa de acierto. A partir de ello, se generan reportes diarios con resúmenes de las actividades y resultados, además de integrar dashboards para visualizar el estado del sistema en tiempo real mediante herramientas como Grafana o Metabase.

Objetivo: ofrecer visibilidad completa sobre el desempeño y la salud del sistema de trading.

⸻

Conclusión

Este proyecto busca construir un sistema integral de trading algorítmico, abarcando desde la adquisición de datos hasta la ejecución automática de órdenes y su monitoreo en producción. La organización por etapas permite avanzar paso a paso, con objetivos claros y resultados medibles en cada fase, garantizando así un desarrollo sólido y escalable.
