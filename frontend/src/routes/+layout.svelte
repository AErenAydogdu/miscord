<script lang="ts">
    import { userStore } from '$lib/userStore';
    import "$lib/styles/main.scss";
    import {ROOT} from "$lib/backend_location";
    import {goto} from "$app/navigation";

    async function logout() {
        await goto("/");
        await fetch(ROOT + "/v1/auth/logout", {
            method: "POST",
            headers: {
                Authorization: $userStore?.token ?? "",
            }
        });

        userStore.set(null);
    }
</script>

<style lang="scss">
    :global(body) {
        margin: 0;
        min-height: 100vh;

        display: flex;
        flex-direction: column;
    }

    header {
        flex-shrink: 1;

        border-bottom: 1px solid gray;
        padding-block: 0.5em;
        padding-inline: 1em;

        display: flex;
        justify-content: start;
        align-items: end;
        gap: 0.75em;
    }

    .content {
        flex-grow: 1;
        position: relative;
    }

    footer {
        flex-shrink: 1;

        border-top: 1px solid gray;
        padding-block: 0.5em;
        padding-inline: 1em;

        text-align: center;
    }

    .brand {
        margin-right: auto;
    }
</style>

<header>
    <a href="/" class="brand">Miscord</a>
    {#if $userStore}
        <span>
            <span class="deemphasis">Logged in as</span>
            {$userStore.username}
        </span>
        <button on:click={logout}>Logout</button>
    {:else}
        <a href="/login">Log in</a>
        <a href="/register">Register</a>
    {/if}
</header>

<div class="content">
    <slot />
</div>

<footer>
    <p class="deemphasis">&copy; 2024, Emre Özcan & A. Eren Aydoğdu.</p>
</footer>
