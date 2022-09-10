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
function get_query(vue) {
  const q = {
    model: deep_copy(vue.model_id),
    parameters: deep_copy(vue.parameters),
    path_initial_image: deep_copy(vue.path_initial_image),
    initial_image_masks: deep_copy(vue.initial_image_masks),
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
  const inputs = document.getElementsByTagName("input");
  for (const inp of inputs) {
    if (inp.id == "control_repeat") {
      continue;
    }
    inp.disabled = st;
  }
  const buttons = document.getElementsByTagName("button");
  for (const inp of buttons) {
    inp.disabled = st;
  }
}

const canvas_max_height = 250;

document.addEventListener("DOMContentLoaded", (event) => {
  const vue = new Vue({
    el: "#app",
    data: {
      model_id: "",
      supported_models: [],
      parameters: {},
      results: [],
      finished: true,
      contorol_repeat: false,
      path_initial_image: null,
      ii_prompt: null,

      use_image_mask: false,
      click_point0: null,
      initial_image_masks: null,
    },
    methods: {
      set_default_parameters: function (dparams) {
        for (const key in dparams) {
          this.$set(this.parameters, key, dparams[key]);
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

        const query = get_query(this);
        query.path = "loading.gif";
        disable_input(true);
        this.results.unshift(query);
        this.finished = false;

        await axios
          .post("/api/generate", query)
          .then((response) => {
            this.results[0] = response.data;
            if (response.data.used_prompt_truncated.length > 0) {
              const tp = response.data.used_prompt_truncated;
              this.results[0].error = `Truncated prompt: ${tp}`;
            }
          })
          .catch((error) => {
            this.results[0].path = "/error.png";
            this.results[0].error = error.response.data.detail;
            console.log(error);
          })
          .finally(() => {
            this.finished = true;
            this.results.splice();
            disable_input(false);
            if (this.results[0].error === undefined && this.contorol_repeat) {
              document.getElementById("input_prompt").value =
                query.parameters.prompt;
              this.action();
            }
          });
      },
      trigger_retry: async function (event) {
        if (event.target.dataset.replace == "yes") {
          this.path_initial_image =
            this.results[event.target.dataset.index].path;
          this.ii_prompt = null;
          return;
        }
        if (event.target.dataset.replace == "plus_20_steps") {
          this.parameters.num_inference_steps =
            this.results[event.target.dataset.index].request.parameters
              .num_inference_steps + 20;
          this.parameters.seed =
            this.results[event.target.dataset.index].request.parameters.seed;
        }
        this.parameters.prompt =
          this.results[event.target.dataset.index].request.parameters.prompt;
        this.action();
      },
      paste_output_json: function (event) {
        const r = deep_copy(this.results[event.target.dataset.index]);
        delete r.used_prompt;
        delete r.used_prompt_tokens;
        delete r.path;
        if (r.request.initial_image_masks !== null) {
          r.masked_img2img = true;
        } else if (r.request.path_initial_image !== null) {
          r.img2img = true;
        }
        delete r.request.path_initial_image;
        delete r.request.initial_image_masks;
        if (r.used_prompt_truncated.length == 0) {
          delete r.used_prompt_truncated;
        }
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
        this.initial_image_masks = [];
        const orig_img = new Image();
        orig_img.src = this.path_initial_image;
        orig_img.addEventListener("load", () => {
          const canvas = document.getElementById("canvas_ii_mask");
          canvas.width = orig_img.width;
          canvas.height = orig_img.height;
          const ctx = canvas.getContext("2d");
          ctx.drawImage(orig_img, 0, 0);
          this.canvas_scale = canvas.height / canvas_max_height;
          canvas.style.width = orig_img.width / this.canvas_scale + "px";
          canvas.style.height = orig_img.height / this.canvas_scale + "px";

          canvas.addEventListener("click", (event) => {
            const rect = event.target.getBoundingClientRect();
            const x = (event.clientX - rect.left) * this.canvas_scale;
            const y = (event.clientY - rect.top) * this.canvas_scale;
            if (this.click_point0 !== null) {
              const pA = this.click_point0;
              const pB = [x, y];
              if (pA[0] > pB[0]) {
                //swap
                const tmp = pA[0];
                pA[0] = pB[0];
                pB[0] = tmp;
              }
              if (pA[1] > pB[1]) {
                //swap
                const tmp = pA[1];
                pA[1] = pB[1];
                pB[1] = tmp;
              }

              ctx.fillRect(pA[0], pA[1], pB[0] - pA[0], pB[1] - pA[1]);
              this.click_point0 = null;
              this.initial_image_masks.push({
                a_x: pA[0],
                a_y: pA[1],
                b_x: pB[0],
                b_y: pB[1],
              });
            } else {
              this.click_point0 = [x, y];
            }
          });
        });
      },
    },

    watch: {
      use_image_mask: function (new_val) {
        if (new_val) {
          this.initialize_mask();
        } else {
          this.initial_image_masks = null;
        }
      },
      path_initial_image: function () {
        this.use_image_mask = false;
      },
    },
  });

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
