<script lang="ts">
    import {type Server, serverList, userStore} from "$lib/userStore";
    import {ROOT} from "$lib/backend_location";
    import {onMount} from "svelte";
    import {goto} from "$app/navigation";

    /** @type {import('./$types').PageData} */
	export let data;

    let server_name_input: HTMLInputElement;
    let server_desc_input: HTMLInputElement;

    let error_message: string | null = null;

    onMount(() => {
        if (!$userStore) {
            goto("/");
        }
    });

    async function create() {
        const new_name = server_name_input.value;
        const new_desc = server_desc_input.value;

        const res = await fetch(ROOT + "/v1/server", {
            method: "POST",
            headers: {
                Authorization: $userStore!.token,
            },
            body: JSON.stringify({
                name: new_name,
                description: new_desc,
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
        <label for="server-name-input">
            Name
            <input
                    type="text"
                    id="server-name-input"
                    bind:this={server_name_input}
                    value="{$userStore?.username}'s place"
                    placeholder="{$userStore?.username}'s place"
            >
        </label>

        <label for="server-description-input">
            Description
            <input
                    type="text"
                    id="server-description-input"
                    bind:this={server_desc_input}
            >
        </label>

        <button on:click={create}>Create!</button>
    </form>
</div>
