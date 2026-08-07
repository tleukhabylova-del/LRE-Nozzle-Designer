"""Constants and propellant reference tables."""

NOZZLE_EXIT_PRESSURE_MAX_MPA = 0.10856

PARA = [
    "Liquid oxygen - Kerosene              ",
    "Liquid oxygen - Liquid hydrogen",
    "Liquid oxygen - Liquid ammonia",
    "Liquid oxygen - UDMH",
    "Nitrogen tetroxide - UDMH",
    "Nitrogen tetroxide - Aerozine 50",
    "Nitrogen tetroxide - Hydrazine",
    "Nitric acid - Kerosene",
    "Nitric acid 70% / Nitrogen oxide 30% - UDMH",
    "Nitric acid 73% / Nitrogen oxide 27% - UDMH",
    "Nitric acid 80% / Nitrogen oxide 20% - UDMH",
    "Nitric acid 73% / Nitrogen oxide 23% - Kerosene",
    "Nitric acid 80% / Nitrogen oxide 20% - Kerosene",
    "Nitric acid 73% / Nitrogen oxide 27% - Tonka 250",
    "Nitric acid 80% / Nitrogen oxide 20% - Tonka 250",
    "Nitric acid - Hydrazine",
]

PARA_DEFAULT = PARA.copy()

PARA_RU = [
    "Жидкий кислород - Керосин              ",
    "Жидкий кислород - Жидкий водород",
    "Жидкий кислород - Жидкий аммиак",
    "Жидкий кислород - НДМГ",
    "Четырехокись азота - НДМГ",
    "Четырехокись азота - Аэрозин 50",
    "Четырехокись азота - Гидразин",
    "Азотная кислота - Керосин",
    "Азотная кислота 70% / Оксид азота 30% - НДМГ",
    "Азотная кислота 73% / Оксид азота 27% - НДМГ",
    "Азотная кислота 80% / Оксид азота 20% - НДМГ",
    "Азотная кислота 73% / Оксид азота 23% - Керосин",
    "Азотная кислота 80% / Оксид азота 20% - Керосин",
    "Азотная кислота 73% / Оксид азота 27% - Тонка 250",
    "Азотная кислота 80% / Оксид азота 20% - Тонка 250",
    "Азотная кислота - Гидразин",
]

k_m_list = [None, 3.40, 4.76, 1.41, 2.14, 3.07, 2.24, 1.44, 5.37, 3.00, 3.35, 3.37, 5.34, 5.37, 2.14, 4.67, 1.45]

R_st_list = [None, 324, 520, 420, 359, 336, 357, 390, 308, 378, 340, 340, 313, 314, 312, 313, 409]

k_st_list = [None, 1.11, 1.22, 1.16, 1.11, 1.13, 1.14, 1.17, 1.13, 1.14, 1.14, 1.14, 1.13, 1.31, 1.13, 1.13, 1.25]

T_st_list = [None, 3631, 3270, 3045, 3575, 3382, 3322, 3231, 3087, 3140, 3134, 3115, 3128, 3107, 3143, 3122, 3045]

J_st_list = [None, 3034, 3286, 3057, 3156, 2950, 2990, 3033, 2730, 2482, 2840, 2831, 2742, 2733, 2745, 2737, 2737]

COEF_J_DEFAULT = 0.95
