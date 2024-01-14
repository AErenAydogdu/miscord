<script lang="ts">
    import {slide} from "svelte/transition";

    import {ROOT} from "$lib/backend_location.js";
    import {goto} from "$app/navigation";

    let username_input: HTMLInputElement;
    let password_input: HTMLInputElement;

    let error_message: string | null = null;
    let successful: boolean = false;

    async function register() {
        const res = await fetch(ROOT + "/v1/auth/register", {
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
            successful = true;
        } else {
            const res_json = await res.json() satisfies {
                error: string
            };

            error_message = res_json.error;
        }
    }
</script>

<style>
    :global(.content) {
        display: grid;
        place-items: center;
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

{#if !successful}
<form id="form">
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

    <button on:click={register}>Register</button>
    <a href="/login" class="deemphasis">login instead?</a>
</form>
{:else}
    <div class="centered">
        <p>Successfully registered!</p>
        <button on:click={() => goto("/login")}>Login</button>
    </div>
{/if}
