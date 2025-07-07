# Quran Art

This project visualizes the use of Arabic demonstratives in the Qur'an. It processes the dataset `qac-with-id.tsv`, which originates from the Qatar Arabic Corpus (University of Oxford) and is licensed under CC BY-SA 3.0. The script transforms linguistic features into simple geometric artwork for each surah.

## Usage

```
python3 quran_art.py
```

Outputs are placed in the `output/` directory:

- `svg/` and `png/` contain one image per surah
- `gallery.html` displays all images in a responsive grid
- `hada_tokens.csv` lists the processed demonstrative tokens

If packages are missing, the script will print a one‑liner:

```
pip install -r requirements.txt
```

The file `requirements.txt` is generated automatically with the exact versions in use.
