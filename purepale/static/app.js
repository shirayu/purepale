function get_query(vue) {
  const q = {
    parameters: vue.parameters,
    path_initial_image: vue.path_initial_image,
    initial_image_masks: vue.initial_image_masks,
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
          })
          .catch((error) => {
            this.results[0].path = "/error.png";
            dom_in.value = this.results[0].parameters.prompt;
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
        const p =
          this.results[event.target.dataset.index].query.parameters.prompt;
        const dom_in = document.getElementById("input_prompt");
        dom_in.value = p;
        this.action();
      },

      action_img2propt: async function () {
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
            console.log(error);
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
