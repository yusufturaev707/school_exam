// Shows admin staff exactly how formulas will look to a pupil, using the same KaTeX as the frontend.
// A mistake in a formula appears here in red, instead of in front of a child during the exam.
window.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".question-preview").forEach(function (element) {
    window.renderMathInElement(element, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
    });
  });
});
