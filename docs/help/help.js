(() => {
  const yearSpan = document.getElementById("current-year");
  if (yearSpan) {
    yearSpan.textContent = new Date().getFullYear().toString();
  }
})();

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function printSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (!section) {
    alert("Unable to locate the requested section for printing.");
    return;
  }

  const title =
    section.dataset.sectionTitle ||
    section.querySelector("h2")?.textContent ||
    "Section";
  const safeTitle = escapeHtml(title);

  const clone = section.cloneNode(true);
  const buttons = clone.querySelectorAll("button");
  buttons.forEach((btn) => btn.remove());

  const printWindow = window.open("", "_blank", "width=850,height=900");

  if (!printWindow) {
    alert("Please allow pop-ups to print individual sections.");
    return;
  }

  const styleLink = document.querySelector('link[rel="stylesheet"][href]');
  const inlineStyle = document.getElementById("inline-help-style");
  let styleBlock = "";
  if (inlineStyle) {
    styleBlock = `<style>${inlineStyle.textContent}</style>`;
  } else if (styleLink) {
    styleBlock = `<link rel="stylesheet" href="${escapeHtml(styleLink.href)}" />`;
  }
  const doc = printWindow.document;
  doc.write(`
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>${safeTitle} – Shigley Solver Pack Help</title>
    ${styleBlock}
    <style>
      body { margin: 32px; background: #ffffff; }
      section { box-shadow: none; border: none; padding: 0; }
      .footer { display: none; }
    </style>
    <script>
      window.MathJax = {
        tex: {
          inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
          displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
        },
        svg: { fontCache: 'global' }
      };
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
  </head>
  <body>
    <section>${clone.innerHTML}</section>
  </body>
</html>`);
  doc.close();

  const finalizePrint = () => {
    printWindow.focus();
    printWindow.print();
  };

  printWindow.addEventListener("load", () => {
    const tryTypeset = () => {
      if (printWindow.MathJax && printWindow.MathJax.typesetPromise) {
        printWindow.MathJax.typesetPromise()
          .then(finalizePrint)
          .catch(finalizePrint);
        return;
      }
      setTimeout(tryTypeset, 120);
    };
    tryTypeset();
  });
}

window.printSection = printSection;
