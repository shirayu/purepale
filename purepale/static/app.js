function deep_copy(val) {
  return JSON.parse(JSON.stringify(val));
}
function copy_to_clipboard(text) {
  const textarea = document.createElement("textarea");
  textarea.style.position = "absolute";
  textarea.style.opacity = 0;
  textarea.style.pointerEvents = "none";
  textarea.value = text;

  document.body.appendChild(textarea);
  textarea.focus();
  textarea.setSelectionRange(0, text.length);
  document.execCommand("copy");
  textarea.parentNode.removeChild(textarea);
}
async function get_query(vue) {
  const canvas_draw = document.getElementById("canvas_ii_mask_draw");
  if (
    vue.use_image_mask &&
    canvas_draw !== undefined &&
    canvas_draw.dataset !== undefined &&
    (vue.path_initial_image_mask === null ||
      parseInt(canvas_draw.dataset.changed) == 1)
  ) {
    //sent mask image
    canvas_draw.dataset.changed = 0;
    const blob = await new Promise((resolve) => canvas_draw.toBlob(resolve));

    const formData = new FormData();
    formData.append("file", blob, "mask.png");
    const request = new Request("/api/upload", {
      method: "POST",
      body: formData,
    });
    await fetch(request)
      .then((response) => {
        return response.json();
      })
      .then((data) => {
        vue.path_initial_image_mask = data.path;
      });
  }

  const q = {
    model: deep_copy(vue.model_id),
    parameters: deep_copy(vue.parameters),
    path_initial_image: deep_copy(vue.path_initial_image),
    path_initial_image_mask: deep_copy(vue.path_initial_image_mask),
  };
  if (typeof q.parameters.seed === "string") {
    if (q.parameters.seed.trim().length == 0) {
      q.parameters.seed = null;
    } else {
      q.parameters.seed = Number(q.parameters.seed);
    }
  }
  return q;
}

function disable_input(st) {
  const inputs = document.querySelectorAll("input,textarea,select,button");
  for (const inp of inputs) {
    if (inp.id == "control_repeat") {
      continue;
    }
    inp.disabled = st;
  }
}

const canvas_max_height = 500;

window.onbeforeunload = function (e) {
  e.returnValue = "Do you really want to close window?";
};

document.addEventListener("DOMContentLoaded", (event) => {
  const vue = Vue.createApp({
    data: () => ({
      model_id: "",
      supported_models: [],
      parameters: {},
      results: [],
      finished: true,
      contorol_repeat: false,
      path_initial_image: null,
      ii_prompt: null,

      use_image_mask: false,
      path_initial_image_mask: null,
    }),

    watch: {
      use_image_mask: function (new_val) {
        if (new_val) {
          this.initialize_mask();
        } else {
          this.path_initial_image_mask = null;
        }
      },
      path_initial_image: function () {
        this.use_image_mask = false;
      },
    },
    methods: {
      set_default_parameters: function (dparams) {
        for (const key in dparams) {
          this.parameters[key] = dparams[key];
        }
      },

      clear_path_initial_image: function () {
        this.path_initial_image = null;
        document.getElementById("file_input_initial_image").value = "";
        this.ii_prompt = null;
      },
      trim_wh_size: function () {
        this.parameters.width = 64 * Math.round(this.parameters.width / 64);
        this.parameters.height = 64 * Math.round(this.parameters.height / 64);
      },
      trigger: async function (event) {
        if (event.keyCode !== 13) {
          return;
        }
        this.action();
      },
      action: async function () {
        const dom_in = document.getElementById("input_prompt");

        const query = await get_query(this);
        disable_input(true);
        this.results.unshift(query);
        this.finished = false;

        await axios
          .post("/api/generate", query)
          .then((response) => {
            this.results[0] = response.data;
            if (response.data.parsed_prompt.used_prompt_truncated.length > 0) {
              const tp = response.data.parsed_prompt.used_prompt_truncated;
              this.results[0].error = `Truncated prompt: ${tp}`;
            }
          })
          .catch((error) => {
            this.results[0].error = error.response.data.detail;
            this.contorol_repeat = false;
            console.log(error);
          })
          .finally(() => {
            this.finished = true;
            this.results.splice();
            disable_input(false);
            if (this.contorol_repeat) {
              this.action();
            }
          });
      },
      trigger_retry: async function (event) {
        if (event.target.dataset.replace == "use_as_ii") {
          this.path_initial_image =
            this.results[event.target.dataset.index].path;
          this.ii_prompt = null;
          return;
        }

        this.parameters = deep_copy(
          this.results[event.target.dataset.index].request.parameters
        );
        this.path_initial_image = deep_copy(
          this.results[event.target.dataset.index].request.path_initial_image
        );
        this.path_initial_image_mask = deep_copy(
          this.results[event.target.dataset.index].request
            .path_initial_image_mask
        );

        if (event.target.dataset.replace == "plus_20_steps") {
          this.model = this.results[event.target.dataset.index].request.model;
          this.parameters.num_inference_steps += 20;
        } else {
          this.parameters.seed = "";
        }
        this.action();
      },
      paste_output_json: function (event) {
        const r = deep_copy(this.results[event.target.dataset.index]);

        {
          delete r.request.parameters.prompt;
          r.parameters = deep_copy(r.request.parameters);

          r.prompt = r.parsed_prompt.used_prompt;
          if (r.parsed_prompt.used_prompt_truncated.length > 0) {
            r.truncated = r.parsed_prompt.used_prompt_truncated;
          }
          if (r.parsed_prompt.tileable) {
            r.tileable = true;
          }
          delete r.parsed_prompt;
        }

        delete r.path;

        {
          if (r.request.path_initial_image_mask !== null) {
            r.masked_img2img = true;
          } else if (r.request.path_initial_image !== null) {
            r.img2img = true;
          } else {
            delete r.parameters.strength;
          }
        }
        delete r.request;
        copy_to_clipboard(JSON.stringify(r, undefined, 2));
        alert("Copied JSON to clipbord!");
      },

      action_img2prompt: async function () {
        const query = {
          path: this.path_initial_image,
        };
        this.ii_prompt = "predicting...";
        await axios
          .post("/api/img2prompt", query)
          .then((response) => {
            this.ii_prompt = response.data.prompt;
          })
          .catch((error) => {
            this.ii_prompt = `${error}`;
          });
      },

      initialize_mask: function () {
        const orig_img = new Image();
        orig_img.src = this.path_initial_image;
        orig_img.addEventListener("load", () => {
          //base canvas
          const canvas_base = document.getElementById("canvas_ii_mask_base");
          canvas_base.width = orig_img.width;
          canvas_base.height = orig_img.height;
          const ctx_base = canvas_base.getContext("2d");
          ctx_base.drawImage(orig_img, 0, 0);
          const canvas_scale = (canvas_base.height / canvas_max_height) * 2;
          canvas_base.style.width = orig_img.width / canvas_scale + "px";
          canvas_base.style.height = orig_img.height / canvas_scale + "px";

          //draw canvas
          const canvas_draw = document.getElementById("canvas_ii_mask_draw");
          canvas_draw.width = canvas_base.width;
          canvas_draw.height = canvas_base.height;
          canvas_draw.style.width = canvas_base.style.width;
          canvas_draw.style.height = canvas_base.style.height;

          const ctx_draw = canvas_draw.getContext("2d");
          ctx_draw.lineWidth = 10;
          const input_lw = document.getElementById("canvas_ii_mask_line_width");
          input_lw.addEventListener("change", (e) => {
            ctx_draw.lineWidth = parseInt(e.target.value);
          });
          input_lw.value = ctx_draw.lineWidth;

          ctx_draw.globalCompositeOperation = "source-over";
          ctx_draw.strokeStyle = "black";
          const object = { handleEvent: DrawWithMouse };

          let draw_started = false;
          canvas_draw.addEventListener("mousedown", drawStart);
          canvas_draw.addEventListener("mouseout", drawEnd);
          canvas_draw.addEventListener("mouseup", drawEnd);
          function draw(x, y) {
            if (draw_started) {
              draw_started = false;
              canvas_draw.dataset.changed = 1;
              ctx_draw.beginPath();
              ctx_draw.moveTo(x, y);
            } else {
              ctx_draw.lineTo(x, y);
            }
            ctx_draw.stroke();
          }

          function drawStart() {
            draw_started = true;
            canvas_draw.addEventListener("mousemove", object);
          }

          function drawEnd() {
            draw_started = false;
            ctx_draw.closePath();
            canvas_draw.removeEventListener("mousemove", object);
          }

          function DrawWithMouse(event) {
            const rect = event.currentTarget.getBoundingClientRect();
            const x = (event.clientX - rect.left) * canvas_scale;
            const y = (event.clientY - rect.top) * canvas_scale;
            draw(x, y);
          }
        });
      },
    },
  }).mount("#app");

  //set default
  axios
    .get("/api/info")
    .then((response) => {
      vue.set_default_parameters(response.data["default_parameters"]);
      for (v of response.data.supported_models) {
        vue.supported_models.push(v);
      }
      vue.supported_models.splice();
      vue.model_id = vue.supported_models[0];
    })
    .catch((error) => {
      alert(`Error: ${error.message}`);
      console.log(error.message);
    });

  const file_input = document.getElementById("file_input_initial_image");
  file_input.addEventListener("change", (event) => {
    if (file_input.files[0]) {
      const formData = new FormData();
      const file = file_input.files[0];
      formData.append("file", file);
      const request = new Request("/api/upload", {
        method: "POST",
        body: formData,
      });
      fetch(request)
        .then((response) => {
          return response.json();
        })
        .then((data) => {
          vue.path_initial_image = data.path;
        });
    }
  });
});
