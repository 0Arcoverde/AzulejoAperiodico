# Azulejo aperiódico

Este repositório reúne materiais para estudar o **Hat**, um monotile aperiódico, e scripts Python que geram desenhos SVG de peças e metatiles. O termo *einstein* usado na literatura significa "uma peça" em alemão; não se refere ao físico Albert Einstein.

A aperiodicidade é uma propriedade de ladrilhamentos infinitos: um patch finito, mesmo quando válido, não prova o resultado. Para explorar o Hat visualmente, consulte o [índice de recursos online](referencias/recursos-online.md), que registra ferramentas, artigos, links de código e a data de consulta.

## Começar

Requisitos: Python 3. Os scripts usam apenas a biblioteca padrão.

Gere um tabuleiro com moldura e os metatiles H, T, P e F nas laterais:

```sh
python3 tabuleiro.py
```

Por padrão, o arquivo `tabuleiro.svg` é criado no diretório atual, com área interna quadrada de 20 cm, borda de 3 cm e metatiles com dimensão máxima igual a duas vezes a espessura da borda. Para alterar esses valores e o nome do SVG:

```sh
python3 tabuleiro.py \
	--tamanho-interno-cm 20 \
	--espessura-borda-cm 3 \
	--multiplicador-perimetro 0.8 \
	--arquivo-saida Tabuleiro.svg
```

`--tamanho-interno-cm` define o lado da área de jogo; `--espessura-borda-cm` define as bordas superior e laterais, enquanto a borda inferior mede `ln(1.5)` vezes esse valor. `--multiplicador-perimetro` controla a maior dimensão dos metatiles em relação à espessura da borda; `--arquivo-saida` escolhe o caminho do SVG. Consulte `python3 tabuleiro.py --help` para os valores padrão.

Para gerar os quatro metatiles-base em uma chapa de 20 × 20 cm:

```sh
python3 metatile.py --max-level 0 --sheet-cm 20 20 --size-cm 3 --output metatiles-base.svg
```

Para construir um patch substituído de nível 1, que contém 29 metatiles:

```sh
python3 metatile.py --max-level 1 --sheet-cm 40 40 --size-cm 3 --output metatiles-nivel-1.svg
```

`--size-cm` define o tamanho da peça Hat de referência; `--sheet-cm` recebe largura e altura da chapa; `--margin-mm` ajusta a margem. `--max-level` aceita níveis de 0 em diante. O SVG mantém peças inteiras dentro da área útil e deduplica arestas de corte compartilhadas.

`azulejo.py` é uma segunda implementação por substituição Sistema-L. Ela escolhe automaticamente o número de iterações a partir do tamanho da chapa e aceita `--sheet-cm`, `--margin-mm`, `--size-cm` e `--output`. Por exemplo:

```sh
python3 azulejo.py --sheet-cm 20 20 --size-cm 3 --margin-mm 10 --output hat-sistema-l.svg
```

## Exemplos

Os SVGs abaixo foram gerados com `metatile.py` e podem ser abertos em um navegador ou editor vetorial:

- [Metatiles-base em chapa de 20 × 20 cm](exemplos/metatiles-base-20cm.svg): H, T, P e F, nível 0.
- [Patch de nível 1 em chapa de 40 × 40 cm](exemplos/metatiles-nivel-1-40cm.svg): 29 metatiles derivados das regras de substituição.

A pasta também contém exemplos de contornos organizados em matrizes de 64 peças, além de [um JSON com os vértices do Hat](exemplos/grade-hat.json):

- [Hat, 5 cm](exemplos/hat-5cm.svg)
- [Turtle, 5 cm](exemplos/turtle-5cm.svg)
- [Tile(1,1), 5 cm](exemplos/tile-1-1-5cm.svg)
- [Spectre, 5 cm](exemplos/spectre-5cm.svg)

Essas quatro matrizes são amostras de formas separadas, não ladrilhamentos montados. `Tile(1,1)` é periódico; Spectre é quiral e tem restrições de orientação. Os SVGs para corte devem ser revisados no software da máquina: confirme cores, camadas, preenchimentos e compensação de kerf antes de fabricar.

## Estrutura

- `azulejo.py`: gerador Sistema-L de patches Hat para chapas.
- `metatile.py`: substituição e exportação dos metatiles H, T, P e F.
- `tabuleiro.py`: tabuleiro físico com moldura e guias de orientação.
- `exemplos/`: SVGs e dados geométricos de demonstração.
- `referencias/`: artigo em PDF, hashes de validação e índice de recursos online.

## Referências e testes

O artigo principal é Smith, Myers, Kaplan e Goodman-Strauss, [*An aperiodic monotile*](https://arxiv.org/abs/2303.10798), arXiv:2303.10798. A pasta `referencias/` inclui o PDF local e `hat-2patch-hashes.txt`, uma fixture de referência para validação combinatória. O [índice de recursos online](referencias/recursos-online.md) reúne também o Hatviz, o código auxiliar e fontes sobre o Spectre. Os SVGs de exemplo podem ser reabertos em um navegador ou editor vetorial para inspeção.