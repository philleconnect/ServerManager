# ServerManager
Base server application for v2

Important: Before releasing an update, set the new version number in `config.py`!

## Service files
Since version 1.2.0, ServerManager natively supports `docker-compose.yml` files. The following structures are supported:

- `services` (we''' name them containers here)
- `networks`
- `volumes`

### Containers
For containers, we respect the following properties (others are ignored):

- `image` OR `path`
- `volumes`
- `networks`
- `ports`
- `env_file`

### Networks
For networks, we respect the following properties (others are ignored):

- `internal`

### Volumes
For volumes, we do not support properties other than the identifier.

### Environment files
Each container gets the environment variables defined in the `.env` files, which are specified in the container's `env_file` section.

A valid `.env` file contains the following lines:

- empty lines
- comments, starting with a `#`
- environment variables, in the form `KEY=VALUE`

Each compose file gets a private environment storage. All new values will be stored there by default. So, multiple compose files can use the same keys. It is possible to define an environment variable as shared.

For ServerManager, the comment line **directly before** a key-value pair is important. It allows to specify the explanation of the key, which is shown in the GUI. Also, it is possible to specify how the key should be handled. After the explanation, add the mode letters you want to use. The following modes are available:

- `M`: mutable. If this is set, the value can be altered in the GUI.
- `U`: use default value. If this is set, the default value provided will be chosen, no need to input a value at first installation.
- `S`: shared value. The value will be taken from (if available) and stored in the global environment storage.

Working example:

```
# This is a mutable value. M
MUTABLE=VALUE_NOT_USED

# This is a unmutable value with a default value. U
UNMUTABLE=FOO

# This is a mutable value with a default value. MU
MUTABLE_WITH_DEFAULT=BAR

# This value is shared with the global store. S
SHARED=VALUE_NOT_USED
```

## Publish a service
Publishing a service involves the following steps:

### Prerequisites:

- The `docker-compose.yml` file and all `.env` files are in the root directory of your git repository.

### Publishing:

- Create a release on GitHub. You don't have to add any artifacts, the auto-generated ones are sufficient.
- Copy the link to the `.tar.gz` file (NOT the `.zip`).
- Add the link as url in the repository.json.
