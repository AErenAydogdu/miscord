<script lang="ts">
    import {slide} from "svelte/transition";

    import {ROOT} from "$lib/backend_location.js";
    import {userStore} from "$lib/userStore";
    import {goto} from "$app/navigation";

    let username_input: HTMLInputElement;
    let password_input: HTMLInputElement;

    let error_message: string | null = null;

    async function login() {
        const res = await fetch(ROOT + "/v1/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: username_input.value,
                password: password_input.value
            })
        })

        if (res.ok) {
            error_message = null;

            const res_json = await res.json() satisfies {
                username: string,
                token: string
            };

            userStore.set(res_json);

            await goto("/");
        } else {
            const res_json = await res.json() satisfies {
                error: string
            };

            error_message = res_json.error;
        }
    }
</script>

<style>
    .center {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }

    form {
        margin-inline: auto;
        width: 36ch;

        display: grid;
        grid-auto-flow: row;
        gap: 1em;
    }

    label {
        display: grid;
        grid-auto-flow: row;
        gap: .25em;
    }
</style>

<form id="form" class="center">
    {#if error_message}
        <p class="toast error" transition:slide>{error_message}</p>
    {/if}

    <label for="username-input">
        Username
        <input type="text" id="username-input" bind:this={username_input}>
    </label>

    <label for="password-input">
        Password
        <input type="password" id="password-input" bind:this={password_input}>
    </label>

    <button on:click={login}>Log in</button>
    <a href="/register" class="deemphasis">register instead?</a>
</form>
