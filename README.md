# Azulejo aperiódico

Projeto sobre o azulejo aperiódico conhecido como **Hat** ("chapéu"), uma peça que cobre o plano, mas não permite uma cobertura periódica. O nome matemático *einstein* vem de *ein Stein* ("uma peça" em alemão) e não é uma referência a Albert Einstein.

## O que as fontes dizem

O artigo de Smith, Myers, Kaplan e Goodman-Strauss apresenta o Hat como um polykite: um polígono composto por oito peças do ladrilhamento de kites. Os autores mostram como cópias da peça formam agrupamentos maiores (*metatiles*) e descrevem regras de substituição que produzem coberturas do plano. Uma análise combinatória assistida por computador demonstra que as coberturas são hierárquicas e, portanto, aperiódicas. O resultado é sobre coberturas infinitas; um arranjo finito de peças pode, naturalmente, repetir padrões.

O arquivo de código auxiliar distribuído com o artigo contém os 13 vértices do contorno `hat_outline` e a definição da grade hexagonal usada por este projeto. O gerador aplica a base dessa grade e substitui os comprimentos 1 e √3 pelo parâmetro `r = b/a` descrito no artigo.

## Jogos e brincadeiras

As atividades abaixo são sugestões para explorar a peça física; não são jogos publicados nem regras apresentadas pelos autores do artigo.

- **Desafio de cobertura:** cada pessoa adiciona uma peça a uma área delimitada, tentando cobrir o máximo possível sem sobreposições ou lacunas. O tabuleiro finito não prova a aperiodicidade do ladrilhamento infinito.
- **Monte o metatile:** em equipe, agrupe peças menores em formas maiores e compare os agrupamentos com as figuras de substituição do artigo.
- **Quebra-cabeça de silhueta:** escolha um contorno desenhado e tente preenchê-lo com as peças, permitindo rotações e reflexões.
- **Continue o padrão:** comece com algumas peças e passe a vez; cada participante acrescenta uma peça que respeite o contorno já montado.
- **Arte em mosaico:** corte várias peças e use cores ou texturas para criar padrões. A decoração é livre e não representa uma regra matemática de encaixe.

## Gerador para corte a laser

O script `gerar_azulejo.py` gera SVGs em milímetros e requer apenas Python 3. No modo `tiling`, parte de um patch Hat de 20 peças publicado como cercável e só aceita extensões que mantenham as 2-coronas completas dentro dos 188 patches validados pelos autores. Cada SVG contém no metadata as transformações e posições usadas; bordas compartilhadas são exportadas uma só vez.

```sh
python3 gerar_azulejo.py --tile hat --size-cm 5 --sheet-cm 40 40 --output hat-40x40.svg
```

`--size-cm` define o diâmetro ponta a ponta da peça: a maior distância entre dois pontos do contorno. `--sheet-cm` recebe largura e altura da chapa e calcula quantas peças cabem, usando 5 mm de margem por padrão (`--margin-mm`). O relatório inclui a compactação do patch e o aproveitamento da chapa. `--count` continua disponível para pedir uma quantidade específica e `--module-mm` define a escala pela grade em vez do diâmetro.

No modo `tiling`, o gerador escreve progresso em `stderr` a cada 2 segundos: peças colocadas, candidatos verificados, tamanho da fronteira, envelope atual e tempo decorrido. Ajuste a frequência com `--progress-interval`; mensagens de progresso não se misturam ao SVG.

O modo `tiling` cresce um patch simplesmente conexo, sem sobreposição nem furos, e filtra 2-coronas completas pelas assinaturas da fixture [hat-2patch-hashes.txt](referencias/hat-2patch-hashes.txt), derivada de `anc/validate/2patches.txt`. A expansão começa com um núcleo menor de 10 peças, correspondente à organização em clusters do artigo, para deixar mais espaço para a busca preencher concavidades da chapa; nessa configuração, a busca encontrou 116 peças e 69,8% de aproveitamento em uma chapa de 40 x 40 cm. É uma heurística: a quantidade encontrada numa chapa não é um ótimo global provado, e a validação local não prova que toda borda incompleta possa ser estendida a uma cobertura infinita. O artigo define os quatro metatiles `T`, `H`, `P` e `F` (com 1, 4, 2 e 2 Hats) e suas regras de substituição em [04_clusters.tex](https://arxiv.org/src/2303.10798) e [05_substitution.tex](https://arxiv.org/src/2303.10798); o gerador atual usa essas regras como base conceitual e mantém a expansão em Hats para preservar a geometria de corte. Use `--layout array` para peças de demonstração separadas em linhas e colunas; nesse modo, `--gap-mm` e `--columns` controlam o espaçamento.

Tipos disponíveis (cada SVG abaixo contém 64 peças de 5 cm em uma matriz 8×8, com 5 mm entre peças):

- `--tile hat`: Hat, com `r = √3` (oito kites): [SVG 64 peças](exemplos/hat-5cm.svg).
- `--tile turtle`: Turtle, com `r = 1/√3` (dez kites): [SVG 64 peças](exemplos/turtle-5cm.svg).
- `--tile equilateral`: `Tile(1,1)`, também denotado `Tile(1)` no artigo; seus 14 lados têm o mesmo comprimento. É um caso periódico, portanto não é um monotile aperiódico: [SVG 64 peças](exemplos/tile-1-1-5cm.svg).
- `--tile family --ratio R`: família `Tile(1,R)` do artigo. O artigo prova a aperiodicidade para `R > 0` e `R ≠ 1`; a família contínua não é formada somente por polykites.
- `--tile spectre --layout array`: polígono quiral Spectre de 14 vértices e lados retos, distinto do Hat e de `Tile(1,1)`. A geometria usa o contorno publicado por [ctkrug/monotile](https://github.com/ctkrug/monotile/blob/main/src/core/spectre.js): [SVG 64 peças](exemplos/spectre-5cm.svg).

Esses arquivos são matrizes de peças separadas para fabricação, não quatro ladrilhamentos montados: o Spectre e `Tile(1,1)` têm requisitos de orientação/quiralidade diferentes, e o encaixe de cada tipo deve ser tratado pelas respectivas regras.

Para usar outro contorno na grade axial triangular, passe um JSON com vértices inteiros. O arquivo de exemplo [exemplos/grade-hat.json](exemplos/grade-hat.json) pode ser editado; lados da grade devem ter comprimento 1, √3 ou 2, e a proporção escolhida precisa fechar o contorno.

```sh
python3 gerar_azulejo.py --layout array --grid-json exemplos/grade-hat.json --ratio 1.4 --size-cm 5 --count 10 --columns 5
```

No modo `tiling`, as faces dos tiles aparecem preenchidas em cinza claro sob os traços vermelhos de corte. Alguns softwares de fabricação podem interpretar o preenchimento como gravação raster; confirme que a camada `tile-fills` será ignorada ou tratada separadamente, além de conferir cor, espessura de linha e compensação de kerf antes de cortar.

### Teste dos arquivos

Depois de gerar um patch Hat, rode o teste que abre o SVG e confere metadata, contagem, sobreposição, furos, 2-coronas e igualdade entre os cortes exportados e a geometria das peças:

```sh
python3 -m unittest discover -s tests -v
```

## Fontes

- Smith, David; Myers, Joseph Samuel; Kaplan, Craig S.; Goodman-Strauss, Chaim. [An aperiodic monotile](https://arxiv.org/abs/2303.10798), arXiv:2303.10798, versão 3, 2024. [PDF baixado para este repositório](referencias/an-aperiodic-monotile.pdf). DOI: [10.5070/C64163843](https://doi.org/10.5070/C64163843).
- [Código auxiliar do artigo no arXiv](https://arxiv.org/src/2303.10798): `anc/validate/hat.py` (contorno `hat_outline`) e `anc/validate/kitegrid.py` (coordenadas da grade).
- Smith, David; Myers, Joseph Samuel; Kaplan, Craig S.; Goodman-Strauss, Chaim. [A chiral aperiodic monotile](https://arxiv.org/abs/2305.17743), arXiv:2305.17743. Fonte para a construção quiral do Spectre e para a restrição de reflexões.
