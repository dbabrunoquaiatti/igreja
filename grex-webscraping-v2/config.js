/**
 * config.js — gerado automaticamente pelo entrypoint.sh em produção.
 *
 * Este arquivo é SOBRESCRITO pelo container ao iniciar.
 * Em desenvolvimento local, preencha os valores abaixo para testar.
 *
 * Variáveis disponíveis (todas lidas via env no entrypoint):
 *   PANEL_TITLE, PRIMARY_COLOR, PRIMARY_LIGHT,
 *   GREX_EMAIL, GREX_PASSWORD,
 *   GREX_PARTICIPANTS_URL, GREX_PARTICIPANTS_URL_2,
 *   GREX_FONTE1_COLUNAS, GREX_FONTE2_COLUNAS,
 *   EXCLUIR_ABAS, EXCLUIR_COLUNAS,
 *   SERVOS, CONVIDADOS, DUPLICADO_IGNORAR,
 *   IGNORA_DISCIPULADOR, PAGAR_DEPOIS_SERVOS, PAGAR_DEPOIS_CONVIDADOS,
 *   MENSAGEM_INSCRICAO, GREX_EVENTO_URL, GREX_AUTOMACAO_CHECKING
 */

window.CONFIG = {
  PANEL_TITLE:             "",
  PRIMARY_COLOR:           "#6b46c1",
  PRIMARY_LIGHT:           "#8b5cf6",
  GREX_EMAIL:              "",
  GREX_PASSWORD:           "",
  GREX_PARTICIPANTS_URL:   "",
  GREX_PARTICIPANTS_URL_2: "",
  GREX_FONTE1_COLUNAS:     "",
  GREX_FONTE2_COLUNAS:     "",
  EXCLUIR_ABAS:            "",
  EXCLUIR_COLUNAS:         "",
  SERVOS:                  "S",
  CONVIDADOS:              "S",
  DUPLICADO_IGNORAR:       "formaPagamento,presenca,dataInscricao",
  IGNORA_DISCIPULADOR:     "",
  PAGAR_DEPOIS_SERVOS:     "0",
  PAGAR_DEPOIS_CONVIDADOS: "0",
  MENSAGEM_INSCRICAO:      "",
  GREX_EVENTO_URL:         "",
  GREX_AUTOMACAO_CHECKING: "",
};

console.log('✅ config.js carregado (dev local)');
