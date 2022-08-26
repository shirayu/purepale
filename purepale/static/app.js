function set_default_parameters(dparams) {
  for (const key in dparams) {
    const dom_in = document.getElementById(`input_${key}`);
    dom_in.value = dparams[key];
  }
}

function get_query(vue) {
  const q = {
    parameters: {},
    prompt: "",
    path_initial_image: vue.path_initial_image,
  };

  const inputs = document.getElementsByTagName("input");
  for (const inp of inputs) {
    const k = inp.id.replace("input_", "");
    if (k == "prompt") {
      q.prompt = inp.value;
    } else {
      q.parameters[k] = inp.value;
    }
  }

  return q;
}

function disable_input(st) {
  const inputs = document.getElementsByTagName("input");
  for (const inp of inputs) {
    if (inp.id == "control_loop") {
      continue;
    }
    inp.disabled = st;
  }
  const buttons = document.getElementsByTagName("button");
  for (const inp of buttons) {
    inp.disabled = st;
  }
}

document.addEventListener("DOMContentLoaded", (event) => {
  const vue = new Vue({
    el: "#app",
    data: {
      results: [],
      finished: true,
      contorol_loop: false,
      path_initial_image: null,
    },
    methods: {
      clear_path_initial_image: function () {
        this.path_initial_image = null;
        document.getElementById("file_input_initial_image").value = "";
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
        disable_input(true);
        this.results.unshift({
          query: query,
          path: "loading.gif",
        });
        this.finished = false;

        await axios
          .post("/api/generate", query)
          .then((response) => {
            const data = response.data;
            this.results[0].path = data.path;
          })
          .catch((error) => {
            this.results[0].path = "/error.png";
            dom_in.value = this.results[0].query.prompt;
            this.results[0].error = error.response.data.detail;
            console.log(error);
          })
          .finally(() => {
            this.finished = true;
            this.results.splice();
            disable_input(false);
            if (this.results[0].error === undefined && this.contorol_loop) {
              document.getElementById("input_prompt").value = query.prompt;
              this.action();
            }
          });
      },
      trigger_retry: async function (event) {
        if (event.target.dataset.replace == "yes") {
          this.path_initial_image =
            this.results[event.target.dataset.index].path;
          return;
        }
        const p = this.results[event.target.dataset.index].query.prompt;
        const dom_in = document.getElementById("input_prompt");
        dom_in.value = p;
        this.action();
      },
    },
  });

  //set default
  axios
    .get("/api/info")
    .then((response) => {
      set_default_parameters(response.data["default_parameters"]);
    })
    .catch((error) => {
      alert(`Error: ${error.message}`);
      console.log(error.message);
    });

  const file_input = document.getElementById("file_input_initial_image");
  file_input.addEventListener("change", (event) => {
    if (file_input.files[0]) {
      const formData = new FormData();
      formData.append("file", file_input.files[0]);
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
