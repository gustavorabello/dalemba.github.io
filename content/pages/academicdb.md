Title: AcademicDB
Slug: academicdb
page_type: academicdb
subtitle: Catalogo academico protegido, gerado a partir dos sources em YAML.


<div id="academicdb-app" class="academicdb-app" data-vault-url="../static/academicdb/vault.json?v=20260915-2010">
  <section class="academicdb-lock" data-lock-screen>
    <div>
      <p class="academicdb-eyebrow">Area protegida</p>
      <h2>AcademicDB</h2>
      <p>Digite a mesma senha do financeiro para descriptografar o catalogo academico no seu navegador.</p>
    </div>
    <form class="academicdb-login" data-login-form>
      <label>
        <span>Senha</span>
        <input type="password" name="password" autocomplete="current-password" required>
      </label>
      <button type="submit">Entrar</button>
      <p class="academicdb-status" data-login-status></p>
    </form>
  </section>

  <section class="academicdb-private" data-private-area hidden>
    <div class="academicdb-shell-header">
      <div>
        <p class="academicdb-eyebrow">Catalogo descriptografado</p>
        <h2>AcademicDB</h2>
      </div>
      <p data-academicdb-summary></p>
    </div>
    <iframe data-academicdb-frame title="AcademicDB protegido" loading="lazy"></iframe>
  </section>
</div>

<script src="../static/js/academicdb.js?v=20260915-2010" defer></script>
