# Recursos online

Links conferidos em 2026-10-02. A data registra a consulta, não a data de publicação.

## Visualização e código

### Hatviz

- **Projeto:** [isohedral/hatviz no GitHub](https://github.com/isohedral/hatviz)
- **Finalidade:** pequeno sketch em p5.js para montar patches do Hat e exibir contornos de metatiles e supertiles. Permite exportar os patches como PNG ou SVG.
- **Código principal do Hatviz:** [`hat.js`](https://github.com/isohedral/hatviz/blob/main/hat.js); utilitários geométricos: [`geometry.js`](https://github.com/isohedral/hatviz/blob/main/geometry.js); página de entrada: [`app.html`](https://github.com/isohedral/hatviz/blob/main/app.html).
- **Acesso:** o README do projeto instrui abrir `app.html` no navegador; ele carrega p5.js online. Para uso local sem essa dependência, o README explica como baixar a biblioteca e ajustar a página. O repositório não informa um endereço de demonstração hospedada.
- **Licença do código:** BSD 3-Clause, conforme o repositório consultado.
- **Dados do GitHub consultados:** repositório público, linguagem principal JavaScript; última atividade de código indicada pela API do GitHub em 2023-06-26. O conteúdo e os metadados podem mudar.

### Código auxiliar do artigo

- [Fontes do artigo no arXiv](https://arxiv.org/src/2303.10798): arquivo fonte com materiais suplementares.
- **Código de validação dos autores:** no pacote de fontes do arXiv, `anc/validate/hat.py` contém o contorno `hat_outline` e `anc/validate/kitegrid.py` define coordenadas da grade. Eles não são arquivos do repositório Hatviz.
- **Acesso:** o pacote pode ser baixado pelo link de fontes do arXiv. Cópia do artigo em PDF e hashes usados pelo gerador estão neste diretório.

### Geometria Spectre

- [`ctkrug/monotile`](https://github.com/ctkrug/monotile): implementação independente que publica o contorno do Spectre em [`src/core/spectre.js`](https://github.com/ctkrug/monotile/blob/main/src/core/spectre.js).
- **Uso neste repositório:** referência geométrica para o exemplo SVG do Spectre; não é uma ferramenta de montagem de ladrilhamentos Hat.

## Artigos e contexto matemático

- Smith, David; Myers, Joseph Samuel; Kaplan, Craig S.; Goodman-Strauss, Chaim. [An aperiodic monotile](https://arxiv.org/abs/2303.10798), arXiv:2303.10798. Apresenta o Hat, os metatiles e a prova de aperiodicidade. DOI da versão publicada: [10.5070/C64163843](https://doi.org/10.5070/C64163843). [PDF local](an-aperiodic-monotile.pdf).
- Smith, David; Myers, Joseph Samuel; Kaplan, Craig S.; Goodman-Strauss, Chaim. [A chiral aperiodic monotile](https://arxiv.org/abs/2305.17743), arXiv:2305.17743. Fonte para a construção quiral Spectre e as restrições de orientação.
- Craig Kaplan. [Página do projeto Hat](https://cs.uwaterloo.ca/~csk/hat/), indicada pelo próprio README do Hatviz como página de contexto e acesso ao artigo.

## Nota de uso

As ferramentas e fontes externas têm escopos diferentes. Hatviz é interativo e explora patches do Hat; o gerador deste repositório cria arquivos SVG para fabricação. Um patch finito válido ou uma imagem não constitui, sozinho, prova da aperiodicidade do ladrilhamento infinito. Consulte as licenças originais antes de reutilizar código ou imagens externos.