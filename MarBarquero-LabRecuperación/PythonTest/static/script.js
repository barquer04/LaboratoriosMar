let preguntas = [];
let indiceActual = 0;
let nivel = "";
let categoria = "";
let respuestasUsuario = [];

document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  nivel = urlParams.get('nivel') || "Fácil";
  categoria = urlParams.get('categoria') || "General";

  fetch(`/questions?nivel=${encodeURIComponent(nivel)}&categoria=${encodeURIComponent(categoria)}`, {
    credentials: 'include'
  })
    .then(res => res.json())
    .then(data => {
      preguntas = data.questions || [];

      if (preguntas.length === 0) {
        document.getElementById("quiz-card").innerHTML = `<p>No se encontraron preguntas para el nivel "${nivel}" y categoría "${categoria}".</p>`;
      } else {
        respuestasUsuario = new Array(preguntas.length).fill(null);
        mostrarPregunta();
        actualizarBarraProgreso();
      }
    })
    .catch(err => {
      console.error("Error al cargar preguntas:", err);
    });

  document.getElementById("siguienteBtn").addEventListener("click", siguientePregunta);
});

function mostrarPregunta() {
  const preguntaObj = preguntas[indiceActual];
  document.getElementById("pregunta").textContent = `(${indiceActual + 1}/${preguntas.length}) ${preguntaObj.pregunta}`;

  const opcionesDiv = document.getElementById("opciones");
  opcionesDiv.innerHTML = "";

  preguntaObj.opciones.forEach(opcion => {
    const btn = document.createElement("button");
    btn.textContent = opcion;
    btn.className = "opcion-btn";

    // Aquí destaco visualmente si la opción seleccionada fue correcta o no
    if (respuestasUsuario[indiceActual] === opcion) {
      btn.style.backgroundColor = (opcion === preguntaObj.respuesta) ? "#4CAF50" : "#E74C3C";
    }

    btn.onclick = () => seleccionarOpcion(btn, opcion, preguntaObj.respuesta);
    opcionesDiv.appendChild(btn);
  });

  document.getElementById("siguienteBtn").disabled = respuestasUsuario[indiceActual] === null;
  actualizarBarraProgreso();
}

function seleccionarOpcion(boton, seleccion, correcta) {
  const botones = document.querySelectorAll(".opcion-btn");
  respuestasUsuario[indiceActual] = seleccion;

  botones.forEach(btn => {
    btn.disabled = true;
    if (btn.textContent === correcta) {
      btn.style.backgroundColor = "#4CAF50"; // marco la respuesta correcta en verde
    } else if (btn.textContent === seleccion) {
      btn.style.backgroundColor = "#E74C3C"; // si se equivocó, la opción seleccionada se marca en rojo
    }
  });

  document.getElementById("siguienteBtn").disabled = false;
}

function siguientePregunta() {
  indiceActual++;
  if (indiceActual < preguntas.length) {
    mostrarPregunta();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } else {
    submitRespuestas();
  }
}

function submitRespuestas() {
  // Aquí calculo cuántas respuestas fueron correctas
  const correctas = respuestasUsuario.filter((respuesta, i) => respuesta === preguntas[i].respuesta).length;
  const total = preguntas.length;
  const puntaje = ((correctas / total) * 100).toFixed(2);

  fetch("/submit_answers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      respuestas: respuestasUsuario,
      nivel: nivel,
      categoria: categoria,
      puntaje: puntaje,
      correctas: correctas,
      total: total
    })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        // Guardo los datos en sessionStorage para mostrarlos luego en el perfil
        sessionStorage.setItem("resultado_quiz", JSON.stringify(responseData));
        window.location.href = "/profile";
      } else {
        alert("Hubo un error al procesar tus respuestas.");
      }
    })
    .catch(err => {
      console.error("Error al enviar respuestas:", err);
      alert("Error de conexión al enviar respuestas.");
    });
}

function actualizarBarraProgreso() {
  const barra = document.getElementById("barra-progreso");
  if (barra) {
    const porcentaje = preguntas.length === 0 ? 0 : Math.round((indiceActual / preguntas.length) * 100);
    barra.style.width = `${porcentaje}%`;
    barra.textContent = `${porcentaje}%`;
  }
}
