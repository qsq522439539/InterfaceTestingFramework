function hello(name) {
    console.log("Hello from privileged code, " + name + "!");
}

Components.utils.exportFunction(hello, unsafeWindow, {defineAs: "hello"});
