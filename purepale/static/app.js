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
        const dom_in = document.getElementById("prompt");
        const query = dom_in.value;
        dom_in.value = "";
        dom_in.disabled = true;
        this.results.unshift({
          prompt: query,
          path: "loading.gif",
        });

        await fetch("/api/generate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ prompt: query }),
        })
          .then((response) => {
            if (!response.ok) {
              console.log("error!");
            }
            console.log("ok!");
            return response.json();
          })
          .then((data) => {
            this.results[0] = {
              prompt: query,
              path: data.path,
            };
            this.results.splice();
            dom_in.disabled = false;
          })
          .catch((error) => {
            console.log(error);
          });
      },
    },
  });
});
