import type { Metadata } from "next";
import {
  AlertTriangle,
  Database,
  ExternalLink,
  FileSearch,
  GitBranch,
  KeyRound,
  LockKeyhole,
  Scale,
  ShieldCheck,
  Workflow,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Sobre | ONGP - PEGA RATAO",
  description:
    "Informacoes sobre finalidade, fontes oficiais, uso das APIs, governanca e LGPD do Observatorio Nacional de Gastos Publicos.",
};

const apiGroups = [
  {
    title: "Transparencia e orcamento federal",
    items: [
      "Portal da Transparencia: despesas, contratos, convenios, emendas, sancoes e remuneracoes quando legalmente permitido.",
      "ComprasGov/ComprasNet Contratos: contratos administrativos e fornecedores vinculados.",
      "Tesouro Transparente: catalogos e conjuntos de dados orcamentarios e fiscais.",
      "dados.gov.br: catalogo federal de bases abertas, ministerios, autarquias e entidades publicas.",
    ],
  },
  {
    title: "Legislativo e eleitoral",
    items: [
      "Camara dos Deputados: deputados, mandatos, orgaos e despesas parlamentares.",
      "Senado Federal: senadores ativos e CEAPS para gastos parlamentares.",
      "TSE: candidatos, cargos, partidos, bens declarados e dados eleitorais publicos.",
    ],
  },
  {
    title: "Cadastro, empresas e sancoes",
    items: [
      "Receita Federal: dados publicos de CNPJ, respeitando finalidade, minimizacao e permissao legal.",
      "TCU e CGU: cadastros publicos de empresas sancionadas, inidoneas ou impedidas, quando disponiveis em API ou arquivo aberto.",
      "IBAMA e CVM: bases abertas de autuacoes, regulacao e informacoes publicas relevantes para cruzamento de risco.",
    ],
  },
  {
    title: "Estados, tribunais e reguladores",
    items: [
      "TCE-SP, TCE-RJ, TCE-PE, TCE-CE e TCE-RN: portais e APIs oficiais de dados abertos quando disponiveis.",
      "Portais estaduais de SP, RJ, MG, SC, RS, PR e BA: catalogos, contratos, despesas e transparencia ativa.",
      "ANEEL, ANTT, ANAC, ANVISA, ANATEL, ANA, ANP, ANTAQ e ANM: bases reguladoras oficiais mapeadas no registro de fontes.",
    ],
  },
];

const safeguards = [
  "Usa preferencialmente bases publicas, dados abertos, convenios formais ou autorizacoes explicitas.",
  "Nao usa CPF integral como chave exibida ao usuario; identificadores pessoais devem ser mascarados.",
  "Separa indicio de conclusao: um alerta aponta risco e evidencia, nao declara culpa.",
  "Registra trilhas de auditoria para acessos, relatorios, disparos de ingestao e acoes administrativas.",
  "Mantem as chaves de API somente no backend, via variaveis de ambiente, sem exposicao no navegador.",
  "Permite revisao humana e rastreabilidade da fonte original antes de qualquer encaminhamento.",
];

const workflow = [
  {
    title: "1. Coleta",
    description:
      "Workers Celery acessam APIs oficiais ou arquivos abertos com rate limit, retries e cabecalhos exigidos por cada fonte.",
  },
  {
    title: "2. Normalizacao",
    description:
      "Dados brutos sao convertidos para modelos de pessoa, empresa, contrato, despesa, orgao e alerta.",
  },
  {
    title: "3. Persistencia",
    description:
      "PostgreSQL guarda dados estruturados, Elasticsearch melhora busca textual e Neo4j conecta pessoas, empresas, orgaos e contratos.",
  },
  {
    title: "4. Inteligencia",
    description:
      "O motor de regras procura fracionamento, concentracao de fornecedor, crescimento anormal e vinculos suspeitos.",
  },
  {
    title: "5. Evidencia",
    description:
      "Dashboards, grafos e relatorios exibem origem, data, valor, fornecedor, documento e explicacao do risco.",
  },
];

const legalLinks = [
  {
    label: "LGPD - Lei 13.709/2018",
    href: "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm",
  },
  {
    label: "LAI - Lei 12.527/2011",
    href: "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm",
  },
  {
    label: "Politica de Dados Abertos - Decreto 8.777/2016",
    href: "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8777.htm",
  },
  {
    label: "ANPD",
    href: "https://www.gov.br/anpd/pt-br",
  },
];

const sourceLinks = [
  {
    label: "Portal da Transparencia",
    href: "https://api.portaldatransparencia.gov.br/api-de-dados",
  },
  {
    label: "Camara dos Deputados - Dados Abertos",
    href: "https://dadosabertos.camara.leg.br/",
  },
  {
    label: "Senado Federal - Dados Abertos",
    href: "https://legis.senado.leg.br/dadosabertos/",
  },
  {
    label: "TSE - Repositorio de Dados Eleitorais",
    href: "https://www.tse.jus.br/eleicoes/estatisticas/repositorio-de-dados-eleitorais-1",
  },
  {
    label: "ComprasGov Contratos",
    href: "https://contratos.comprasnet.gov.br/",
  },
  {
    label: "Portal Brasileiro de Dados Abertos",
    href: "https://dados.gov.br/swagger-ui/index.html",
  },
];

function SectionTitle({
  eyebrow,
  title,
  description,
  tone = "default",
}: {
  eyebrow: string;
  title: string;
  description?: string;
  tone?: "default" | "inverted";
}) {
  const isInverted = tone === "inverted";

  return (
    <div className="max-w-3xl">
      <p
        className={
          isInverted
            ? "text-xs font-semibold uppercase tracking-wider text-emerald-300"
            : "text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300"
        }
      >
        {eyebrow}
      </p>
      <h2
        className={
          isInverted
            ? "mt-2 text-2xl font-semibold text-white"
            : "mt-2 text-2xl font-semibold text-slate-950 dark:text-white"
        }
      >
        {title}
      </h2>
      {description ? (
        <p
          className={
            isInverted
              ? "mt-3 text-sm leading-6 text-slate-300"
              : "mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300"
          }
        >
          {description}
        </p>
      ) : null}
    </div>
  );
}

function ExternalResourceLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:text-emerald-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-emerald-700 dark:hover:text-emerald-300"
      href={href}
      rel="noreferrer"
      target="_blank"
    >
      {label}
      <ExternalLink className="h-4 w-4" aria-hidden="true" />
    </a>
  );
}

export default function SobrePage() {
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-10">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.8fr] lg:items-start">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
              Observatorio Nacional de Gastos Publicos
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white sm:text-4xl">
              ONGP - PEGA RATAO
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
              O ONGP e uma plataforma GovTech/CivicTech para centralizar,
              monitorar, auditar e correlacionar gastos publicos brasileiros.
              O sistema cruza dados oficiais de despesas, contratos,
              fornecedores, partidos, cargos, orgaos e documentos para
              transformar informacao fragmentada em evidencias rastreaveis.
            </p>
            <div className="mt-6 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950 dark:border-amber-900/70 dark:bg-amber-950/30 dark:text-amber-100">
              <strong className="font-semibold">Importante:</strong> o ONGP
              identifica sinais de risco e inconsistencias para auditoria. Ele
              nao declara culpa, nao substitui investigacao oficial e deve ser
              usado com revisao humana, fonte original e contexto juridico.
            </div>
          </div>

          <div className="grid gap-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex items-center gap-3">
                <ShieldCheck className="h-5 w-5 text-emerald-700 dark:text-emerald-300" />
                <h2 className="text-sm font-semibold text-slate-950 dark:text-white">
                  Legalidade por desenho
                </h2>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                Bases publicas, minimizacao de dados, auditoria de acesso,
                mascaramento e controle por perfil.
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex items-center gap-3">
                <GitBranch className="h-5 w-5 text-sky-700 dark:text-sky-300" />
                <h2 className="text-sm font-semibold text-slate-950 dark:text-white">
                  Inteligencia em grafo
                </h2>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                Neo4j relaciona pessoas, empresas, contratos, orgaos,
                fornecedores, socios e alertas.
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex items-center gap-3">
                <FileSearch className="h-5 w-5 text-orange-700 dark:text-orange-300" />
                <h2 className="text-sm font-semibold text-slate-950 dark:text-white">
                  Evidencia verificavel
                </h2>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                Cada alerta deve apontar valor, data, fonte, documento e regra
                aplicada.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <Database className="h-6 w-6 text-emerald-700 dark:text-emerald-300" />
          <h2 className="mt-4 text-base font-semibold text-slate-950 dark:text-white">
            O que monitora
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            Pessoas publicas, cargos, orgaos, contratos, fornecedores,
            despesas, emendas, licitacoes e documentos oficiais.
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <Workflow className="h-6 w-6 text-sky-700 dark:text-sky-300" />
          <h2 className="mt-4 text-base font-semibold text-slate-950 dark:text-white">
            Como funciona
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            Coleta por APIs, normaliza no PostgreSQL, indexa para busca,
            sincroniza grafos e aplica regras de risco.
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <AlertTriangle className="h-6 w-6 text-orange-700 dark:text-orange-300" />
          <h2 className="mt-4 text-base font-semibold text-slate-950 dark:text-white">
            Para que serve
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            Apoiar auditorias, controle social, jornalismo investigativo,
            pesquisa publica e priorizacao de casos com maior risco.
          </p>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <SectionTitle
          eyebrow="Pipeline"
          title="Do dado bruto ao alerta explicavel"
          description="A plataforma foi desenhada para preservar rastreabilidade: dado coletado, origem, transformacao, relacionamento e regra aplicada."
        />
        <div className="mt-6 grid gap-4 lg:grid-cols-5">
          {workflow.map((step) => (
            <div
              className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950"
              key={step.title}
            >
              <h3 className="text-sm font-semibold text-slate-950 dark:text-white">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <SectionTitle
          eyebrow="APIs oficiais"
          title="Quais fontes o ONGP usa"
          description="O arquivo de fontes do backend mapeia APIs e catalogos oficiais. Conectores ativos rodam automaticamente; fontes catalogadas ficam prontas para ativacao apos transformador especifico e validacao juridica."
        />
        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          {apiGroups.map((group) => (
            <div
              className="rounded-lg border border-slate-200 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-950"
              key={group.title}
            >
              <h3 className="text-base font-semibold text-slate-950 dark:text-white">
                {group.title}
              </h3>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {group.items.map((item) => (
                  <li className="flex gap-3" key={item}>
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600 dark:bg-emerald-300" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          {sourceLinks.map((link) => (
            <ExternalResourceLink href={link.href} key={link.href} label={link.label} />
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <SectionTitle
          eyebrow="Uso seguro das chaves"
          title="Como o sistema acessa as APIs"
          description="As chamadas oficiais sao feitas pelo backend FastAPI e pelos workers Celery. O frontend nunca deve receber chaves sensiveis."
        />
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-center gap-3">
              <KeyRound className="h-5 w-5 text-emerald-700 dark:text-emerald-300" />
              <h3 className="text-sm font-semibold text-slate-950 dark:text-white">
                Variaveis de ambiente
              </h3>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Chaves como <code className="rounded bg-slate-200 px-1.5 py-0.5 text-xs dark:bg-slate-800">CGU_API_KEY</code>,
              <code className="ml-1 rounded bg-slate-200 px-1.5 py-0.5 text-xs dark:bg-slate-800">PORTAL_TRANSPARENCIA_API_KEY</code>
              e credenciais de provedores externos devem ficar no ambiente de
              execucao, no GitHub Secrets ou no cofre de segredos da nuvem.
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-center gap-3">
              <LockKeyhole className="h-5 w-5 text-sky-700 dark:text-sky-300" />
              <h3 className="text-sm font-semibold text-slate-950 dark:text-white">
                Camada de backend
              </h3>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
              O backend injeta cabecalhos exigidos pelas APIs, como
              <code className="ml-1 rounded bg-slate-200 px-1.5 py-0.5 text-xs dark:bg-slate-800">chave-api-dados</code>,
              aplica timeout, retries, logs e controle de taxa para preservar
              estabilidade e auditoria.
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <SectionTitle
          eyebrow="LGPD, LAI e governanca"
          title="Regras de conformidade adotadas"
          description="O ONGP e orientado por transparencia publica, minimizacao de dados pessoais e controles proporcionais ao risco."
        />
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_0.8fr]">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-950">
            <div className="flex items-center gap-3">
              <Scale className="h-5 w-5 text-emerald-700 dark:text-emerald-300" />
              <h3 className="text-base font-semibold text-slate-950 dark:text-white">
                Compromissos praticos
              </h3>
            </div>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {safeguards.map((item) => (
                <li className="flex gap-3" key={item}>
                  <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700 dark:text-emerald-300" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-950">
            <h3 className="text-base font-semibold text-slate-950 dark:text-white">
              Referencias legais
            </h3>
            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
              A operacao deve observar a Lei Geral de Protecao de Dados, a Lei
              de Acesso a Informacao, a Politica de Dados Abertos e orientacoes
              da Autoridade Nacional de Protecao de Dados.
            </p>
            <div className="mt-5 flex flex-col gap-3">
              {legalLinks.map((link) => (
                <ExternalResourceLink
                  href={link.href}
                  key={link.href}
                  label={link.label}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-slate-950 p-6 text-white shadow-sm dark:border-slate-800 sm:p-8">
        <SectionTitle
          eyebrow="Limites conhecidos"
          title="O que o ONGP nao deve fazer"
          description="A plataforma existe para apoiar controle e investigacao responsavel. Alguns limites sao parte do desenho de seguranca."
          tone="inverted"
        />
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <h3 className="text-sm font-semibold text-white">Nao expor dados sensiveis</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Dados pessoais restritos, CPF integral e bases sigilosas exigem
              autorizacao legal, perfil adequado e parecer especifico.
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <h3 className="text-sm font-semibold text-white">Nao automatizar condenacao</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Alertas sao sinais de auditoria. Toda conclusao depende de
              contexto, contraditorio, documentacao e autoridade competente.
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <h3 className="text-sm font-semibold text-white">Nao esconder a fonte</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Relatorios e dashboards devem manter a origem do dado, a data da
              coleta, a regra aplicada e o link do documento quando houver.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
