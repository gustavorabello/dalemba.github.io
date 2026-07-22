Title: Financeiro
Slug: financeiro
page_type: financeiro
subtitle: O site completo do financeiroDB, atualizado e protegido por senha.


<div id="financeiro-app" class="financeiro-app" data-vault-url="https://dalembinha.github.io/static/financeiro/vault.json?v=20260721-1147">
  <section class="financeiro-lock" data-lock-screen>
    <div>
      <p class="financeiro-eyebrow">Área protegida</p>
      <h2>Financeiro</h2>
      <p>Digite a senha para abrir a versão atualizada do financeiroDB no seu navegador.</p>
    </div>
    <form class="financeiro-login" data-login-form>
      <label>
        <span>Senha</span>
        <input type="password" name="password" autocomplete="current-password" required>
      </label>
      <button type="submit">Entrar</button>
      <p class="financeiro-status" data-login-status></p>
    </form>
  </section>

  <section class="financeiro-private" data-private-area hidden>
    <div class="financeiro-shell-header">
      <div>
        <p class="financeiro-eyebrow">Site descriptografado</p>
        <h2>financeiroDB</h2>
      </div>
      <p data-financeiro-summary></p>
    </div>
    <iframe data-financeiro-frame title="financeiroDB protegido"></iframe>
  </section>
</div>

<script src="../static/js/financeiro.js?v=20260721-1147" defer></script>
