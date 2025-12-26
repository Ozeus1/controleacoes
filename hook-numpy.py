# Hook customizado para NumPy 2.x no PyInstaller
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Coletar todos os submódulos do NumPy
hiddenimports = collect_submodules('numpy')

# Adicionar módulos críticos do NumPy 2.x
hiddenimports += [
    'numpy._core',
    'numpy._core._multiarray_umath',
    'numpy._core._exceptions',
    'numpy._core._dtype',
    'numpy._core._methods',
    'numpy._core.multiarray',
    'numpy._core.umath',
    'numpy.core._multiarray_umath',
    'numpy.core._dtype_ctypes',
]

# Coletar arquivos de dados do NumPy
datas = collect_data_files('numpy')
