from pathlib import Path
from re import compile, UNICODE

# ============= color configs =============
INFO = "\033[96m<INFO>\033[0m"
OK = "\033[92m<OK>\033[0m"
ERROR = "\033[91m<ERROR>\033[0m"
# color blue
cb = lambda text: f"\033[96m{text}\033[0m"

# ============= OCR configs =============
BASE_URL = 'https://github.com/tesseract-ocr/tessdata/raw/main/' # (в конце обязательно /)
LANGUAGES = {
	'rus': 'rus.traineddata',
	'eng': 'eng.traineddata'
}
CFD = Path(__file__).resolve().parent # (current file directory)
TESSDATA_DIR = CFD / 'tessdata' # (tessdata directory)

# ============= Transfer configs =============
OUTLINE_COLOR = (255, 0, 0) # (R, G, B)
OUTLINE_FACTOR = 0.005

# ============= parsers configs =============
#FILE_REGEX = compile(r'^([A-Za-zА-Яа-яЁё_0-9]+)-([\d._]*)-((?:\d{8})?)-(\d{1,2})-(\d)-([A-Za-zА-Яа-яЁё_.]*)(?:@([A-Za-zА-Яа-яЁё0-9_]+))?\.(\w+)')
FILE_REGEX = compile(
    r'^([^-.]+)-([\d._]*)-((?:\d{8})?)-(\d{1,2})-(\d)-([^@.]*)(?:@([^.]*))?\.(\w+)',
    UNICODE
)
TEMP_FOLDER = './temp' # ./tmp нельзя
