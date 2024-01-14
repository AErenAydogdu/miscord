<script lang="ts">
    import {type Server, serverList, userStore} from "$lib/userStore";
    import {ROOT} from "$lib/backend_location";
    import {onMount} from "svelte";
    import {goto} from "$app/navigation";

    /** @type {import('./$types').PageData} */
	export let data;

    let code_input: HTMLInputElement;

    let error_message: string | null = null;

    onMount(() => {
        if (!$userStore) {
            goto("/");
        }
    });

    async function join() {
        let code = code_input.value;

        code = code.replace(/[ıiİ]/g, "I");
        code = code.replace(/[^a-zA-Z0-9]/g, "");
        code = code.toUpperCase();

        const res = await fetch(ROOT + "/v1/member", {
            method: "POST",
            headers: {
                Authorization: $userStore!.token,
            },
            body: JSON.stringify({
                code: code,
            }),
        });

        const json = await res.json();
        if (!res.ok) {
            error_message = json.error;
            return;
        }

        serverList.update((servers) => {
            if (!servers) {
                return [json];
            }
            servers.push(json);
            return servers;
        });

        await goto("/chat/" + json.id);
    }
</script>

<style>
    .content {
        max-width: 72ch;
        margin-inline: auto;
    }

    form {
        margin-top: 2.5em;
        display: grid;
        gap: 1em;
    }

    label {
        display: grid;
        gap: 0.1em;
    }
</style>

<div class="content">
    {#if error_message}
        <p class="toast">{error_message}</p>
    {/if}

    <form>
        <label for="code-input">
            Code
            <input
                    type="text"
                    id="code-input"
                    bind:this={code_input}
                    placeholder="6 character invite code"
            >
        </label>

        <button on:click={join}>Join!</button>
    </form>
</div>
