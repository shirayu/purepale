function set_default_parameters(dparams) {
  for (const key in dparams) {
    const dom_in = document.getElementById(`input_${key}`);
    dom_in.value = dparams[key];
  }
}

function get_query() {
  const q = {
    parameters: {},
    prompt: "",
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

document.addEventListener("DOMContentLoaded", (event) => {
  new Vue({
    el: "#app",
    data: {
      results: [],
    },
    methods: {
      trigger: async function (event) {
        if (event.keyCode !== 13) {
          return;
        }
        this.action();
      },
      action: async function () {
        const dom_in = document.getElementById("input_prompt");

        const query = get_query();
        dom_in.value = "";
        dom_in.disabled = true;
        this.results.unshift({
          query: query,
          path: "loading.gif",
        });

        await fetch("/api/generate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(query),
        })
          .then((response) => {
            if (!response.ok) {
              this.results[0].path = "/error.png";
            }
            return response.json();
          })
          .then((data) => {
            if (data.path !== undefined) {
              this.results[0].path = data.path;
            } else {
              dom_in.value = this.results[0].query.prompt;
              this.results[0].query.prompt += `: ${data.detail}`;
            }
            this.results.splice();
            dom_in.disabled = false;
          })
          .catch((error) => {
            console.log(error);
          });
      },
      trigger_retry: async function (event) {
        const p = this.results[event.target.dataset.index].query.prompt;
        const dom_in = document.getElementById("input_prompt");
        dom_in.value = p;
        this.action();
      },
    },
  });

  //set default
  fetch("/api/info")
    .then((response) => {
      if (!response.ok) {
        console.log("error!");
      }
      return response.json();
    })
    .then((data) => {
      set_default_parameters(data["default_parameters"]);
    })
    .catch((error) => {
      console.log(error);
    });
});
